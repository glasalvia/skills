#!/usr/bin/env bash
# sonarr-series-search.sh — Busca series en Sonarr por nombre
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
sonarr-series-search.sh — Busca series en Sonarr por término

USO:
  sonarr-series-search.sh --term <texto>

ARGUMENTOS:
  --term   Término de búsqueda (obligatorio)

SALIDA:
  JSON array con tvdbId, title, year, status, overview, network

EJEMPLO:
  sonarr-series-search.sh --term "Breaking Bad"
EOF
    exit 0
fi

TERM=""
if [[ "${1:-}" == "--term" && -n "${2:-}" ]]; then
    TERM="$2"
fi

if [[ -z "$TERM" ]]; then
    echo '{"error":"Se requiere --term <texto>","code":"MISSING_TERM"}' >&2
    exit 3
fi

# URL-encode term
ENCODED_TERM=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${TERM}'))" 2>/dev/null || echo "$TERM")

"${SCRIPT_DIR}/call-api.sh" sonarr GET "/api/v3/series/lookup?term=${ENCODED_TERM}"