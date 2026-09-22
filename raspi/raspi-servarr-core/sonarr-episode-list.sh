#!/usr/bin/env bash
# sonarr-episode-list.sh — Lista episodios de una serie en Sonarr
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
sonarr-episode-list.sh — Lista episodios de una serie en Sonarr

USO:
  sonarr-episode-list.sh --series-id <id> [--season <num>]

ARGUMENTOS:
  --series-id  ID de la serie (obligatorio)
  --season     Número de temporada (opcional)

SALIDA:
  JSON array con episodeId, seasonNumber, episodeNumber, title, airDate, monitored, hasFile

EJEMPLOS:
  sonarr-episode-list.sh --series-id 1
  sonarr-episode-list.sh --series-id 1 --season 3
EOF
    exit 0
fi

SERIES_ID=""
SEASON=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --series-id) SERIES_ID="$2"; shift 2 ;;
        --season) SEASON="$2"; shift 2 ;;
        *) echo "{\"error\":\"Argumento desconocido: $1\",\"code\":\"INVALID_ARG\"}" >&2; exit 3 ;;
    esac
done

if [[ -z "$SERIES_ID" ]]; then
    echo '{"error":"Se requiere --series-id <id>","code":"MISSING_SERIES_ID"}' >&2
    exit 3
fi

RESPONSE=$("${SCRIPT_DIR}/call-api.sh" sonarr GET "/api/v3/episode?seriesId=${SERIES_ID}") || {
    echo "$RESPONSE" >&2
    exit 1
}

# Filtrar por temporada si se especificó
if [[ -n "$SEASON" ]]; then
    echo "$RESPONSE" | python3 -c "
import sys, json
episodes = json.load(sys.stdin)
filtered = [e for e in episodes if e.get('seasonNumber') == int(${SEASON})]
print(json.dumps(filtered, indent=2))
" 2>/dev/null || echo "$RESPONSE"
else
    echo "$RESPONSE"
fi