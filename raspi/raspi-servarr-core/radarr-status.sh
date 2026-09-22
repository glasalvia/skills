#!/usr/bin/env bash
# radarr-status.sh — Estado del sistema Radarr
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
radarr-status.sh — Muestra estado del sistema Radarr

USO:
  radarr-status.sh

SALIDA:
  JSON con versión, uptime, databaseType, startTime, etc.

CÓDIGOS:
  0   Éxito
  1   Error de API
  2   Error de configuración
EOF
    exit 0
fi

"${SCRIPT_DIR}/call-api.sh" radarr GET /api/v3/system/status