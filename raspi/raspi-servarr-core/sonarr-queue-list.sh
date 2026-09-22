#!/usr/bin/env bash
# sonarr-queue-list.sh — Muestra la cola de descargas activas de Sonarr
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
sonarr-queue-list.sh — Muestra la cola de descargas activas en Sonarr

USO:
  sonarr-queue-list.sh [--include-unknown true/false]

ARGUMENTOS:
  --include-unknown  Incluir episodios de estado desconocido (default: false)

SALIDA:
  JSON array con id, seriesTitle, episodeTitle, seasonNumber, progress, status, estimatedCompletionTime

EJEMPLO:
  sonarr-queue-list.sh
EOF
    exit 0
fi

INCLUDE_UNKNOWN="false"

if [[ "${1:-}" == "--include-unknown" ]]; then
    INCLUDE_UNKNOWN="${2:-false}"
fi

RESPONSE=$("${SCRIPT_DIR}/call-api.sh" sonarr GET "/api/v3/queue?includeUnknownSeriesItems=${INCLUDE_UNKNOWN}") || {
    echo "$RESPONSE" >&2
    exit 1
}

echo "$RESPONSE"