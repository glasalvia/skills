#!/usr/bin/env bash
# sonarr-series-list.sh — Lista series en Sonarr
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
sonarr-series-list.sh — Lista todas las series en Sonarr

USO:
  sonarr-series-list.sh [--filter <estado>]

FILTROS:
  continuing  Solo series en emisión
  ended       Solo series finalizadas
  all         Todas (por defecto)

SALIDA:
  JSON array con id, title, year, status, monitored, seasonCount, path

EJEMPLOS:
  sonarr-series-list.sh
  sonarr-series-list.sh --filter continuing
EOF
    exit 0
fi

FILTER="all"
if [[ "${1:-}" == "--filter" && -n "${2:-}" ]]; then
    FILTER="$2"
fi

RESPONSE=$("${SCRIPT_DIR}/call-api.sh" sonarr GET /api/v3/series) || {
    echo "$RESPONSE" >&2
    exit 1
}

# Aplicar filtro si es necesario
if [[ "$FILTER" == "all" ]]; then
    echo "$RESPONSE"
else
    echo "$RESPONSE" | python3 -c "
import sys, json
series = json.load(sys.stdin)
filtered = [s for s in series if s.get('status', '').lower() == '$FILTER']
print(json.dumps(filtered, indent=2))
" 2>/dev/null || echo "$RESPONSE"
fi