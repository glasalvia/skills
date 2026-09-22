#!/usr/bin/env bash
# radarr-movie-list.sh — Lista películas en Radarr
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
radarr-movie-list.sh — Lista todas las películas en Radarr

USO:
  radarr-movie-list.sh [--filter <estado>]

FILTROS:
  downloaded  Películas descargadas
  missing     Películas faltantes
  available   Películas disponibles (descargadas + en biblioteca)
  all         Todas (por defecto)

SALIDA:
  JSON array con id, title, year, status, monitored, hasFile, path

EJEMPLOS:
  radarr-movie-list.sh
  radarr-movie-list.sh --filter missing
EOF
    exit 0
fi

FILTER="all"
if [[ "${1:-}" == "--filter" && -n "${2:-}" ]]; then
    FILTER="$2"
fi

RESPONSE=$("${SCRIPT_DIR}/call-api.sh" radarr GET /api/v3/movie) || {
    echo "$RESPONSE" >&2
    exit 1
}

# Aplicar filtro si no es "all"
if [[ "$FILTER" != "all" ]]; then
    echo "$RESPONSE" | python3 -c "
import sys, json
movies = json.load(sys.stdin)
if '$FILTER' == 'downloaded':
    filtered = [m for m in movies if m.get('hasFile', False)]
elif '$FILTER' == 'missing':
    filtered = [m for m in movies if not m.get('hasFile', True)]
elif '$FILTER' == 'available':
    filtered = [m for m in movies if m.get('status', '') == 'released' or m.get('hasFile', False)]
else:
    filtered = movies
print(json.dumps(filtered, indent=2))
" 2>/dev/null || echo "$RESPONSE"
else
    echo "$RESPONSE"
fi