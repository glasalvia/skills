#!/usr/bin/env bash
# sonarr-series-add.sh — Agrega una serie a Sonarr
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
sonarr-series-add.sh — Agrega una serie a Sonarr

USO:
  sonarr-series-add.sh --tvdb-id <id> [opciones]

ARGUMENTOS:
  --tvdb-id         ID de TVDB (obligatorio)
  --root-folder     Ruta de destino (opcional, auto-detecta)
  --quality-profile ID numérico de perfil de calidad (opcional, auto-detecta)
  --quality         Nombre del perfil: 720p, 1080p, any, sd (opcional, auto-detecta)
  --monitored       Monitorear episodios (opcional, default: true)
  --search          Buscar episodios faltantes (opcional, default: true)

SALIDA:
  JSON con la serie creada o existente

EJEMPLOS:
  sonarr-series-add.sh --tvdb-id 376524
  sonarr-series-add.sh --tvdb-id 376524 --root-folder /media/series --quality-profile 4
  sonarr-series-add.sh --tvdb-id 376524 --quality 720p
EOF
    exit 0
fi

# Parse args
TVDB_ID=""
ROOT_FOLDER=""
QUALITY_PROFILE=""
QUALITY_NAME=""
MONITORED="true"
SEARCH="true"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tvdb-id) TVDB_ID="$2"; shift 2 ;;
        --root-folder) ROOT_FOLDER="$2"; shift 2 ;;
        --quality-profile) QUALITY_PROFILE="$2"; shift 2 ;;
        --quality) QUALITY_NAME="$2"; shift 2 ;;
        --monitored) MONITORED="$2"; shift 2 ;;
        --search) SEARCH="$2"; shift 2 ;;
        *) echo "{\"error\":\"Argumento desconocido: $1\",\"code\":\"INVALID_ARG\"}" >&2; exit 3 ;;
    esac
done

if [[ -z "$TVDB_ID" ]]; then
    echo '{"error":"Se requiere --tvdb-id <id>","code":"MISSING_TVDB_ID"}' >&2
    exit 3
fi

# Auto-detect root folder si no se especificó
if [[ -z "$ROOT_FOLDER" ]]; then
    ROOT_FOLDER=$("${SCRIPT_DIR}/call-api.sh" sonarr GET /api/v3/rootfolder 2>/dev/null | python3 -c "
import sys, json
try:
    folders = json.load(sys.stdin)
    if folders:
        print(folders[0].get('path', ''))
except Exception: pass
" 2>/dev/null || echo "")
    if [[ -z "$ROOT_FOLDER" ]]; then
        ROOT_FOLDER="/media/series"
    fi
fi

# Resolver perfil de calidad
# Si se especificó --quality (nombre), buscar por nombre en la API
if [[ -n "$QUALITY_NAME" ]]; then
    QUALITY_PROFILE=$("${SCRIPT_DIR}/call-api.sh" sonarr GET /api/v3/qualityprofile 2>/dev/null | python3 -c "
import sys, json, re
try:
    profiles = json.load(sys.stdin)
    term = '${QUALITY_NAME,,}'
    alias_map = {
        '4k': '2160p',
        'uhd': '2160p',
        'ultra': '2160p',
        'hd': '720p',
        'sd': '480p',
        'fullhd': '1080p',
        'full-hd': '1080p',
        'remux': 'remux',
    }
    if term in alias_map:
        term = alias_map[term]
    for p in profiles:
        if p['name'].lower() == term:
            print(p['id'])
            sys.exit(0)
    for p in profiles:
        if p['name'].lower() != 'any' and term in p['name'].lower():
            print(p['id'])
            sys.exit(0)
    for p in profiles:
        if p['name'].lower() == 'any':
            continue
        items = [i.get('quality',{}).get('name','').lower() for i in p.get('items',[]) if i.get('allowed')]
        if any(term in qual for qual in items):
            print(p['id'])
            sys.exit(0)
    for p in profiles:
        if p['name'].lower() == 'any':
            print(p['id'])
            sys.exit(0)
    print(profiles[0]['id'])
except Exception:
    print('ERROR')
" 2>/dev/null || echo "")
    if [[ -z "$QUALITY_PROFILE" || "$QUALITY_PROFILE" == "NOT_FOUND" || "$QUALITY_PROFILE" == "ERROR" ]]; then
        echo "{\"error\":\"Perfil de calidad no encontrado: ${QUALITY_NAME}\",\"code\":\"QUALITY_NOT_FOUND\"}" >&2
        exit 3
    fi
fi

# Auto-detect quality profile si no se especificó
if [[ -z "$QUALITY_PROFILE" ]]; then
    QUALITY_PROFILE=$("${SCRIPT_DIR}/call-api.sh" sonarr GET /api/v3/qualityprofile 2>/dev/null | python3 -c "
import sys, json
try:
    profiles = json.load(sys.stdin)
    if profiles:
        print(profiles[0].get('id', 1))
except Exception: pass
" 2>/dev/null || echo "1")
fi

# Buscar serie por tvdbId para obtener datos completos
LOOKUP_RESULT=$("${SCRIPT_DIR}/call-api.sh" sonarr GET "/api/v3/series/lookup?term=tvdb:${TVDB_ID}" 2>/dev/null) || {
    echo '{"error":"No se pudo buscar la serie por tvdbId","code":"LOOKUP_FAILED"}' >&2
    exit 1
}

# Extraer datos de la serie
SERIES_JSON=$(echo "$LOOKUP_RESULT" | python3 "${SCRIPT_DIR}/_helpers/build_payload.py" sonarr "${TVDB_ID}" "${QUALITY_PROFILE}" "${ROOT_FOLDER}" "${MONITORED}" "${SEARCH}") || {
    echo '{"error":"Error construyendo payload de serie","code":"BUILD_ERROR"}' >&2
    exit 1
}

# Verificar si hubo error en la extracción
if echo "$SERIES_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('error') else 1)" 2>/dev/null; then
    echo "$SERIES_JSON" >&2
    exit 1
fi

# Enviar POST para agregar la serie
RESULT=$("${SCRIPT_DIR}/call-api.sh" sonarr POST /api/v3/series "$SERIES_JSON") || {
    ERROR_CODE=$?
    # Si el error es 409 (conflict), la serie ya existe
    echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'already' in json.dumps(d).lower() else 1)" 2>/dev/null && {
        echo "{\"status\":\"already_exists\",\"tvdbId\":${TVDB_ID}}"
        exit 0
    }
    echo "$RESULT" >&2
    exit $ERROR_CODE
}

echo "$RESULT"