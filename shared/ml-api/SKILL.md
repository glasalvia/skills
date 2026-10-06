---
name: "ml-api"
description: "Recuperar datos de artículos de MercadoLibre (descripciones, preguntas, vendedor) mediante API autenticada con client_credentials."
---

# MercadoLibre API — Consulta de artículos de terceros

## Propósito
Recuperar datos estructurados de artículos de MercadoLibre desde la API oficial, incluyendo artículos **de terceros vendedores** (no solo los propios). La API de MercadoLibre bloquea `GET /items/{id}` para terceros (403 PolicyAgent), pero endpoints secundarios permanecen accesibles y son la fuente de datos de esta skill.

## Endpoints verificados

### Accesibles (funcionan para artículos de terceros)

| Endpoint | Descripción |
|---|---|
| `GET /items/{id}/description` | Texto descriptivo del vendedor (plain_text) + **snapshot.url** (imagen JPG de la descripción) |
| `GET /questions/search?item={id}&limit=N&offset=N` | Preguntas y respuestas (paginado) |
| `GET /users/{seller_id}` | Información pública del vendedor (reputación, ubicación, transacciones) |

### Bloqueados para terceros

| Endpoint | Resultado |
|---|---|
| `GET /items/{id}` | ❌ 403 PolicyAgent |
| `GET /items?ids={id}` | ❌ 403 por cada ítem en body |
| `GET /reviews/item/{id}` | ❌ 403 forbidden |

## Autenticación

### Credenciales

Las credenciales de la app de MercadoLibre se almacenan en:
```
workspace/secrets/mercado_libre_token.txt
```

Formato del archivo:
```
ML_APP_ID:<app_id>
CLIENT_SECRET:<client_secret>
```

### Flujo de autenticación

Usar `grant_type=client_credentials`:

```
POST https://api.mercadolibre.com/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
client_id=<ML_APP_ID>
client_secret=<CLIENT_SECRET>
```

Respuesta:
```json
{
  "access_token": "APP_USR-{app_id}-{random}-{user_id}",
  "token_type": "Bearer",
  "expires_in": 21600,
  "scope": "offline_access read ..."
}
```

El token expira en 6 horas (21600 segundos). Para simplificar, se genera uno nuevo en cada invocación.

### NOTA CRÍTICA SOBRE LA INYECCIÓN DE SECRETOS

La sintaxis `***'VAR')` de OpenClaw **NO funciona** dentro de:
- Scripts Python escritos a disco y ejecutados con `python3 <archivo>`
- Heredocs (`<< 'EOF'`)
- Comandos multilínea en `exec`

**Forma correcta**: leer las credenciales desde el archivo de secrets usando `open()` en Python, o acceder directamente con `os.environ.get('VAR')` cuando la variable de entorno esté disponible.

**NO usar** `***})` en headers de Python ni en strings f (`f'Bearer ***}'`). Usar concatenación simple:

```python
req.add_header('Authorization', 'Bearer ' + access_token)
```

## Scripts

### `scripts/ml_api.py`
Biblioteca Python reutilizable. Funciones exportadas:

- `read_credentials()` → `(app_id, client_secret)`
- `get_token(app_id, client_secret)` → `access_token`
- `api_get(url, token)` → `dict` (JSON parseado)

### `scripts/ml_full_item_data.py`
Script autónomo que obtiene todos los datos disponibles de un artículo:

```
python3 scripts/ml_full_item_data.py <ITEM_ID>
```

Retorna: descripción, preguntas (últimas 3), datos del vendedor.

### `scripts/ml_test_all_endpoints.py`
Barrido de todos los endpoints documentados para un artículo dado.

## Uso desde el agente

### Desde shell
```bash
cd workspace && python3 scripts/ml_api.py <ITEM_ID> description
cd workspace && python3 scripts/ml_api.py <ITEM_ID> questions
```

### Desde Python
```python
from ml_api import read_credentials, get_token, api_get

app_id, client_secret = ***)
token = ***, client_secret)
```

### Obtención del vendedor desde preguntas
```python
qs = api_get(f'https://api.mercadolibre.com/questions/search?item={item_id}&limit=1', token)
seller_id = qs['questions'][0]['seller_id']
seller = api_get(f'https://api.mercadolibre.com/users/{seller_id}', token)
```

## IDs comunes

| Propósito | ID |
|---|---|
| `MLA1533603971` | Puerta Granero de Pino Plegable 90x210 |
| `MLA2567934822` | Puerta Granero Los Pinos 90x200 + 3 Vidrios |
| `177115370` | Vendedor ABERTURASTF |
| `1131768178` | Vendedor PUERTASGRANEROLOSPINOS |