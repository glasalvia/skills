#!/usr/bin/env bash
# radarr-movie-add.sh — Agrega una película a Radarr
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
radarr-movie-add.sh — Agrega una película a Radarr

USO:
  radarr-movie-add.sh --tmdb-id <id> [opciones]

ARGUMENTOS:
  --tmdb-id         ID de TMDB (obligatorio)
  --root-folder     Ruta de destino (opcional, auto-detecta)
  --quality-profile ID de perfil de calidad (opcional, auto-detecta)
  --monitored       Monitorear (opcional, default: true)
  --search          Buscar para descarga (opcional, default: true)

SALIDA:
  JSON con la película creada o existente

EJEMPLOS:
  radarr-movie-add.sh --tmdb-id 603
  radarr-movie-add.sh --tmdb-id 603 --root-folder /media/movies --quality-profile 4
EOF
    exit 0
fi

TMDB_ID=""
ROOT_FOLDER=""
QUALITY_PROFILE=""
MONITORED="true"
SEARCH="true"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tmdb-id) TMDB_ID="$2"; shift 2 ;;
        --root-folder) ROOT_FOLDER="$2"; shift 2 ;;
        --quality-profile) QUALITY_PROFILE="$2"; shift 2 ;;
        --monitored) MONITORED="$2"; shift 2 ;;
        --search) SEARCH="$2"; shift 2 ;;
        *) echo "{\"error\":\"Argumento desconocido: $1\",\"code\":\"INVALID_ARG\"}" >&2; exit 3 ;;
    esac
done

if [[ -z "$TMDB_ID" ]]; then
    echo '{"error":"Se requiere --tmdb-id <id>","code":"MISSING_TMDB_ID"}' >&2
    exit 3
fi

# Auto-detect root folder
if [[ -z "$ROOT_FOLDER" ]]; then
    ROOT_FOLDER=$("${SCRIPT_DIR}/call-api.sh" radarr GET /api/v3/rootfolder 2>/dev/null | python3 -c "
import sys, json
try:
    folders = json.load(sys.stdin)
    if folders:
        print(folders[0].get('path', ''))
except: pass
" 2>/dev/null || echo "")
    if [[ -z "$ROOT_FOLDER" ]]; then
        ROOT_FOLDER="/media/movies"
    fi
fi

# Auto-detect quality profile
if [[ -z "$QUALITY_PROFILE" ]]; then
    QUALITY_PROFILE=$("${SCRIPT_DIR}/call-api.sh" radarr GET /api/v3/qualityprofile 2>/dev/null | python3 -c "
import sys, json
try:
    profiles = json.load(sys.stdin)
    if profiles:
        print(profiles[0].get('id', 1))
except: pass
" 2>/dev/null || echo "1")
fi

# Buscar película por tmdbId
LOOKUP_RESULT=$("${SCRIPT_DIR}/call-api.sh" radarr GET "/api/v3/movie/lookup?term=tmdb:${TMDB_ID}" 2>/dev/null) || {
    echo '{"error":"No se pudo buscar la película por tmdbId","code":"LOOKUP_FAILED"}' >&2
    exit 1
}

# Construir payload
MOVIE_JSON=$(echo "$LOOKUP_RESULT" | python3 -c "
import sys, json
try:
    results = json.load(sys.stdin)
    if not results:
        print(json.dumps({'error': 'Película no encontrada con tmdbId: ${TMDB_ID}', 'code': 'NOT_FOUND'}))
        sys.exit(1)
    m = results[0]
    payload = {
        'tmdbId': m.get('tmdbId', ${TMDB_ID}),
        'title': m.get('title', ''),
        'titleSlug': m.get('titleSlug', ''),
        'images': m.get('images', []),
        'year': m.get('year', 0),
        'qualityProfileId': int(${QUALITY_PROFILE}),
        'rootFolderPath': '${ROOT_FOLDER}',
        'monitored': ${MONITORED},
        'minimumAvailability': 'announced',
        'addOptions': {
            'searchForMovie': ${SEARCH}
        }
    }
    print(json.dumps(payload))
except Exception as e:
    print(json.dumps({'error': str(e), 'code': 'PARSE_ERROR'}))
    sys.exit(1)
") || {
    echo '{"error":"Error parseando resultado de búsqueda","code":"PARSE_ERROR"}' >&2
    exit 1
}

# Verificar error
if echo "$MOVIE_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('error') else 1)" 2>/dev/null; then
    echo "$MOVIE_JSON" >&2
    exit 1
fi

# POST para agregar
RESULT=$("${SCRIPT_DIR}/call-api.sh" radarr POST /api/v3/movie "$MOVIE_JSON") || {
    ERROR_CODE=$?
    echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'already' in json.dumps(d).lower() else 1)" 2>/dev/null && {
        echo "{\"status\":\"already_exists\",\"tmdbId\":${TMDB_ID}}"
        exit 0
    }
    echo "$RESULT" >&2
    exit $ERROR_CODE
}

echo "$RESULT"