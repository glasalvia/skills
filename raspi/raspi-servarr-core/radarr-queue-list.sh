#!/usr/bin/env bash
# radarr-queue-list.sh — Muestra la cola de descargas activas de Radarr
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
radarr-queue-list.sh — Muestra la cola de descargas activas en Radarr

USO:
  radarr-queue-list.sh

SALIDA:
  JSON array con id, movieTitle, quality, progress, status, estimatedCompletionTime

EJEMPLO:
  radarr-queue-list.sh
EOF
    exit 0
fi

"${SCRIPT_DIR}/call-api.sh" radarr GET /api/v3/queue