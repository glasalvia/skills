#!/usr/bin/env bash
# radarr-movie-delete.sh — Elimina una película de Radarr
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
radarr-movie-delete.sh — Elimina una película de Radarr

USO:
  radarr-movie-delete.sh --id <movieId> [--delete-files true/false]

ARGUMENTOS:
  --id            ID de la película (obligatorio)
  --delete-files  Eliminar archivos del disco (opcional, default: false)

SALIDA:
  {"status":"deleted","movieId":<id>}

EJEMPLO:
  radarr-movie-delete.sh --id 1
EOF
    exit 0
fi

MOVIE_ID=""
DELETE_FILES="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --id) MOVIE_ID="$2"; shift 2 ;;
        --delete-files) DELETE_FILES="$2"; shift 2 ;;
        *) echo "{\"error\":\"Argumento desconocido: $1\",\"code\":\"INVALID_ARG\"}" >&2; exit 3 ;;
    esac
done

if [[ -z "$MOVIE_ID" ]]; then
    echo '{"error":"Se requiere --id <movieId>","code":"MISSING_ID"}' >&2
    exit 3
fi

ENDPOINT="/api/v3/movie/${MOVIE_ID}?deleteFiles=${DELETE_FILES}"
RESULT=$("${SCRIPT_DIR}/call-api.sh" radarr DELETE "$ENDPOINT") || {
    echo "{\"status\":\"deleted\",\"movieId\":${MOVIE_ID}}"
    exit 0
}

echo "{\"status\":\"deleted\",\"movieId\":${MOVIE_ID}}"