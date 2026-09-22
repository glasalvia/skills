#!/usr/bin/env bash
# sonarr-status.sh — Estado del sistema Sonarr
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
sonarr-status.sh — Muestra estado del sistema Sonarr

USO:
  sonarr-status.sh

SALIDA:
  JSON con versión, uptime, databaseType, startTime, etc.

CÓDIGOS:
  0   Éxito
  1   Error de API
  2   Error de configuración
EOF
    exit 0
fi

"${SCRIPT_DIR}/call-api.sh" sonarr GET /api/v3/system/status