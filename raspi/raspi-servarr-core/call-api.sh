#!/usr/bin/env bash
#
# call-api.sh — Wrapper universal de autenticación para Servarr APIs
#
# Uso: call-api.sh <servicio> <method> <endpoint> [body]
#
# Servicios: sonarr, radarr
# Métodos: GET, POST, PUT, DELETE
#
# Códigos de retorno:
#   0 = éxito
#   1 = error de API (timeout, conexión, HTTP != 2xx)
#   2 = error de configuración (archivo no encontrado, variable faltante)
#   3 = argumentos inválidos
#
# Dependencias: curl

set -euo pipefail

CONFIG_FILE="${HOME}/.servarr-keys.conf"
TIMEOUT=10

# --- Help ---
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
call-api.sh — Wrapper universal de APIs Servarr

USO:
  call-api.sh <servicio> <method> <endpoint> [body]
  call-api.sh --help

SERVICIOS:
  sonarr   Controla Sonarr (series TV)
  radarr   Controla Radarr (películas)

MÉTODOS:
  GET      Consultar recursos
  POST     Crear recursos o ejecutar comandos
  PUT      Actualizar recursos
  DELETE   Eliminar recursos

ENDPOINT:
  Ruta absoluta de la API, ej: /api/v3/system/status

BODY:
  Para POST/PUT, pasar JSON como string o "-" para leer de stdin

CÓDIGOS DE RETORNO:
  0   Éxito
  1   Error de API
  2   Error de configuración
  3   Argumentos inválidos

EJEMPLOS:
  call-api.sh sonarr GET /api/v3/system/status
  call-api.sh radarr GET /api/v3/movie
  call-api.sh sonarr POST /api/v3/series '{"tvdbId": 376524}'
  echo '{"tvdbId": 376524}' | call-api.sh sonarr POST /api/v3/series -

CONFIG:
  ~/.servarr-keys.conf debe contener:
    SONARR_URL=http://localhost:8989
    SONARR_API_KEY=abc123
    RADARR_URL=http://localhost:7878
    RADARR_API_KEY=xyz789
EOF
    exit 0
fi

# --- Argumentos ---
if [[ $# -lt 3 ]]; then
    echo '{"error":"Argumentos insuficientes. Uso: call-api.sh <servicio> <method> <endpoint> [body]","code":"INVALID_ARGS"}' >&2
    exit 3
fi

SERVICE="${1,,}"
METHOD=$(echo "$2" | tr '[:lower:]' '[:upper:]')
ENDPOINT="$3"
BODY="${4:-}"

# --- Validar servicio ---
case "$SERVICE" in
    sonarr|radarr) ;;
    *)
        echo "{\"error\":\"Servicio desconocido: $SERVICE. Servicios válidos: sonarr, radarr\",\"code\":\"INVALID_SERVICE\"}" >&2
        exit 3
        ;;
esac

# --- Validar método ---
case "$METHOD" in
    GET|POST|PUT|DELETE) ;;
    *)
        echo "{\"error\":\"Método inválido: $METHOD. Métodos válidos: GET, POST, PUT, DELETE\",\"code\":\"INVALID_METHOD\"}" >&2
        exit 3
        ;;
esac

# --- Cargar configuración ---
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "{\"error\":\"Archivo de configuración no encontrado: $CONFIG_FILE\",\"code\":\"CONFIG_NOT_FOUND\"}" >&2
    exit 2
fi

# shellcheck source=/dev/null
source "$CONFIG_FILE"

# Determinar URL y API key según servicio
SERVICE_VAR=$(echo "$SERVICE" | tr '[:lower:]' '[:upper:]')
URL_VAR="${SERVICE_VAR}_URL"
KEY_VAR="${SERVICE_VAR}_API_KEY"

BASE_URL="${!URL_VAR:-}"
API_KEY="${!KEY_VAR:-}"

if [[ -z "$BASE_URL" ]]; then
    echo "{\"error\":\"Variable ${URL_VAR} no definida en ${CONFIG_FILE}\",\"code\":\"CONFIG_MISSING_URL\"}" >&2
    exit 2
fi

if [[ -z "$API_KEY" ]]; then
    echo "{\"error\":\"Variable ${KEY_VAR} no definida en ${CONFIG_FILE}\",\"code\":\"CONFIG_MISSING_KEY\"}" >&2
    exit 2
fi

# --- Construir URL completa ---
FULL_URL="${BASE_URL}${ENDPOINT}"

# --- Construir headers ---
declare -a CURL_ARGS=(
    --silent
    --max-time "$TIMEOUT"
    --connect-timeout 5
    --request "$METHOD"
    --header "X-Api-Key: ${API_KEY}"
)

# --- Body handling ---
if [[ -n "$BODY" ]]; then
    if [[ "$BODY" == "-" ]]; then
        CURL_ARGS+=(--data-binary @-)
    else
        CURL_ARGS+=(--data "$BODY")
    fi
    CURL_ARGS+=(--header "Content-Type: application/json")
fi

# --- Ejecutar curl ---
HTTP_RESPONSE=$(mktemp)
HTTP_CODE=$(curl "${CURL_ARGS[@]}" --write-out "%{http_code}" --output "$HTTP_RESPONSE" "$FULL_URL" 2>/dev/null) || {
    EXIT_CODE=$?
    rm -f "$HTTP_RESPONSE"
    if [[ $EXIT_CODE -eq 28 ]]; then
        echo "{\"error\":\"Timeout conectando a ${BASE_URL}\",\"code\":\"TIMEOUT\"}" >&2
    else
        echo "{\"error\":\"Error de conexión a ${BASE_URL} (curl exit code ${EXIT_CODE})\",\"code\":\"CONNECTION_ERROR\"}" >&2
    fi
    exit 1
}

# --- Leer respuesta ---
RESPONSE_BODY=$(cat "$HTTP_RESPONSE")
rm -f "$HTTP_RESPONSE"

# --- Verificar código HTTP ---
if [[ "$HTTP_CODE" -lt 200 || "$HTTP_CODE" -ge 300 ]]; then
    # Intentar parsear error JSON de la API
    ERROR_MSG=$(echo "$RESPONSE_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('message',''))" 2>/dev/null || echo "$RESPONSE_BODY")
    echo "{\"error\":\"HTTP ${HTTP_CODE}: ${ERROR_MSG}\",\"code\":\"HTTP_ERROR\"}" >&2
    exit 1
fi

# --- Retornar respuesta ---
echo "$RESPONSE_BODY"
exit 0