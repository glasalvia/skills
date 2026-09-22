#!/usr/bin/env bash
# radarr-movie-search.sh — Busca películas en Radarr por nombre
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
radarr-movie-search.sh — Busca películas en Radarr por término

USO:
  radarr-movie-search.sh --term <texto>

ARGUMENTOS:
  --term   Término de búsqueda (obligatorio)

SALIDA:
  JSON array con tmdbId, title, year, status, overview, studio

EJEMPLO:
  radarr-movie-search.sh --term "The Matrix"
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

ENCODED_TERM=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${TERM}'))" 2>/dev/null || echo "$TERM")

"${SCRIPT_DIR}/call-api.sh" radarr GET "/api/v3/movie/lookup?term=${ENCODED_TERM}"