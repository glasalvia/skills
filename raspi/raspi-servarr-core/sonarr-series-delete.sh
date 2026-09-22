#!/usr/bin/env bash
# sonarr-series-delete.sh — Elimina una serie de Sonarr
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
sonarr-series-delete.sh — Elimina una serie de Sonarr

USO:
  sonarr-series-delete.sh --id <seriesId> [--delete-files true/false]

ARGUMENTOS:
  --id            ID de la serie (obligatorio)
  --delete-files  Eliminar archivos del disco (opcional, default: false)

SALIDA:
  {"status":"deleted","seriesId":<id>}

EJEMPLO:
  sonarr-series-delete.sh --id 1
  sonarr-series-delete.sh --id 1 --delete-files true
EOF
    exit 0
fi

SERIES_ID=""
DELETE_FILES="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --id) SERIES_ID="$2"; shift 2 ;;
        --delete-files) DELETE_FILES="$2"; shift 2 ;;
        *) echo "{\"error\":\"Argumento desconocido: $1\",\"code\":\"INVALID_ARG\"}" >&2; exit 3 ;;
    esac
done

if [[ -z "$SERIES_ID" ]]; then
    echo '{"error":"Se requiere --id <seriesId>","code":"MISSING_ID"}' >&2
    exit 3
fi

ENDPOINT="/api/v3/series/${SERIES_ID}?deleteFiles=${DELETE_FILES}"
RESULT=$("${SCRIPT_DIR}/call-api.sh" sonarr DELETE "$ENDPOINT") || {
    echo "{\"status\":\"deleted\",\"seriesId\":${SERIES_ID}}"
    exit 0
}

echo "{\"status\":\"deleted\",\"seriesId\":${SERIES_ID}}"