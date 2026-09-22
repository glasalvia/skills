#!/usr/bin/env bash
# sonarr-episode-search.sh — Gatilla búsqueda de episodios faltantes en Sonarr
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
sonarr-episode-search.sh — Busca episodios faltantes de una serie en Sonarr

USO:
  sonarr-episode-search.sh --series-id <id>

ARGUMENTOS:
  --series-id  ID de la serie (obligatorio)

SALIDA:
  {"status":"search_triggered","seriesId":<id>,"commandId":<id>}

EJEMPLO:
  sonarr-episode-search.sh --series-id 1
EOF
    exit 0
fi

SERIES_ID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --series-id) SERIES_ID="$2"; shift 2 ;;
        *) echo "{\"error\":\"Argumento desconocido: $1\",\"code\":\"INVALID_ARG\"}" >&2; exit 3 ;;
    esac
done

if [[ -z "$SERIES_ID" ]]; then
    echo '{"error":"Se requiere --series-id <id>","code":"MISSING_SERIES_ID"}' >&2
    exit 3
fi

# Obtener episodios de la serie que no tienen archivo
EPISODES=$("${SCRIPT_DIR}/call-api.sh" sonarr GET "/api/v3/episode?seriesId=${SERIES_ID}") || {
    echo "$EPISODES" >&2
    exit 1
}

# Extraer IDs de episodios faltantes
EPISODE_IDS=$(echo "$EPISODES" | python3 -c "
import sys, json
try:
    episodes = json.load(sys.stdin)
    missing = [str(e['id']) for e in episodes if not e.get('hasFile', True)]
    print(','.join(missing))
except Exception as e:
    print('ERROR: ' + str(e))
    sys.exit(1)
") || {
    echo "{\"error\":\"Error parseando episodios\",\"code\":\"PARSE_ERROR\"}" >&2
    exit 1
}

if [[ -z "$EPISODE_IDS" ]]; then
    echo "{\"status\":\"no_missing_episodes\",\"seriesId\":${SERIES_ID}}"
    exit 0
fi

# Construir comando de búsqueda
COMMAND_JSON=$(python3 -c "
import json
ids = [int(x) for x in '${EPISODE_IDS}'.split(',') if x.strip()]
print(json.dumps({
    'name': 'EpisodeSearch',
    'episodeIds': ids
}))
")

RESULT=$("${SCRIPT_DIR}/call-api.sh" sonarr POST /api/v3/command "$COMMAND_JSON") || {
    echo "$RESULT" >&2
    exit 1
}

COMMAND_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id','unknown'))" 2>/dev/null || echo "unknown")
echo "{\"status\":\"search_triggered\",\"seriesId\":${SERIES_ID},\"commandId\":${COMMAND_ID}}"