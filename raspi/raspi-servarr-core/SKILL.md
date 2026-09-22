---
name: "raspi-servarr-core"
description: "Control nativo de Sonarr y Radarr vía scripts bash. Listar, buscar, agregar y eliminar series/películas con comandos atómicos."
---

# raspi-servarr-core

## Descripción

Skill que habilita al agente Raspi para controlar **Sonarr** (series TV) y **Radarr** (películas) mediante scripts bash. Cada script ejecuta una operación atómica contra la API REST correspondiente y retorna JSON estructurado.

## Dependencias

- Servicios: Sonarr (puerto 8989), Radarr (puerto 7878)
- `curl` — HTTP requests
- `python3` — parseo JSON (fallback sin `jq`)

## Configuración inicial

Crear `~/.servarr-keys.conf` con permisos 600:

```bash
cp ~/skills/raspi/raspi-servarr-core/servarr-keys.conf.example ~/.servarr-keys.conf
chmod 600 ~/.servarr-keys.conf
# Editar con nano/vim y reemplazar los *** con las API keys reales
```

Contenido esperado:
```
SONARR_URL="http://localhost:8989"
SONARR_API_KEY="<key>"
RADARR_URL="http://localhost:7878"
RADARR_API_KEY="<key>"
```

## Scripts disponibles

### Sonarr

| Comando | Sintaxis | Descripción |
|---|---|---|
| `sonarr-status.sh` | `sonarr-status.sh` | Estado del sistema Sonarr |
| `sonarr-series-list.sh` | `sonarr-series-list.sh [--filter continuing\|ended\|all]` | Lista series |
| `sonarr-series-search.sh` | `sonarr-series-search.sh --term "<nombre>"` | Busca series por nombre |
| `sonarr-series-add.sh` | `sonarr-series-add.sh --tvdb-id <id> [--root-folder] [--quality-profile] [--monitored] [--search]` | Agrega serie |
| `sonarr-series-delete.sh` | `sonarr-series-delete.sh --id <seriesId> [--delete-files true]` | Elimina serie |
| `sonarr-episode-list.sh` | `sonarr-episode-list.sh --series-id <id> [--season <num>]` | Lista episodios |
| `sonarr-episode-search.sh` | `sonarr-episode-search.sh --series-id <id>` | Busca episodios faltantes |
| `sonarr-queue-list.sh` | `sonarr-queue-list.sh [--include-unknown true]` | Cola de descargas |

### Radarr

| Comando | Sintaxis | Descripción |
|---|---|---|
| `radarr-status.sh` | `radarr-status.sh` | Estado del sistema Radarr |
| `radarr-movie-list.sh` | `radarr-movie-list.sh [--filter downloaded\|missing\|available\|all]` | Lista películas |
| `radarr-movie-search.sh` | `radarr-movie-search.sh --term "<nombre>"` | Busca películas |
| `radarr-movie-add.sh` | `radarr-movie-add.sh --tmdb-id <id> [--root-folder] [--quality-profile] [--monitored] [--search]` | Agrega película |
| `radarr-movie-delete.sh` | `radarr-movie-delete.sh --id <movieId> [--delete-files true]` | Elimina película |
| `radarr-queue-list.sh` | `radarr-queue-list.sh` | Cola de descargas |

## Mapeo de intención → comando

Cuando recibas una solicitud en lenguaje natural, mapeá al script correspondiente:

### Series (Sonarr)

| Intención del usuario | Comando a ejecutar |
|---|---|
| "listame las series" / "qué series tengo" | `sonarr-series-list.sh` |
| "buscá la serie <nombre>" | `sonarr-series-search.sh --term "<nombre>"` |
| "agregá <nombre> a Sonarr" | Buscar con `sonarr-series-search.sh`, extraer tvdbId, luego `sonarr-series-add.sh --tvdb-id <id>` |
| "eliminá la serie <id> de Sonarr" | `sonarr-series-delete.sh --id <id>` |
| "mostrame los episodios de la serie <id>" | `sonarr-episode-list.sh --series-id <id>` |
| "buscá episodios faltantes de la serie <id>" | `sonarr-episode-search.sh --series-id <id>` |
| "cómo va la descarga de series" / "colade series" | `sonarr-queue-list.sh` |
| "estado de Sonarr" | `sonarr-status.sh` |

### Películas (Radarr)

| Intención del usuario | Comando a ejecutar |
|---|---|
| "listame las películas" / "qué películas tengo" | `radarr-movie-list.sh` |
| "mostrame las faltantes" | `radarr-movie-list.sh --filter missing` |
| "buscá <película> en Radarr" | `radarr-movie-search.sh --term "<nombre>"` |
| "agregá <película> a Radarr" | Buscar con `radarr-movie-search.sh`, extraer tmdbId, luego `radarr-movie-add.sh --tmdb-id <id>` |
| "eliminá la película <id> de Radarr" | `radarr-movie-delete.sh --id <id>` |
| "cómo va la descarga de películas" / "cola" | `radarr-queue-list.sh` |
| "estado de Radarr" | `radarr-status.sh` |

## Códigos de retorno

| Código | Significado |
|---|---|
| 0 | Éxito |
| 1 | Error de API (timeout, conexión, HTTP != 2xx) |
| 2 | Error de configuración (archivo no encontrado, variable faltante) |
| 3 | Argumentos inválidos |

## Ejemplos de flujo completo

### Agregar una serie nueva

```
1. sonarr-series-search.sh --term "Silo"
   → JSON con tvdbId: 376524
2. sonarr-series-add.sh --tvdb-id 376524
   → JSON con serie creada
```

### Agregar una película nueva

```
1. radarr-movie-search.sh --term "Dune Part Two"
   → JSON con tmdbId: 693134
2. radarr-movie-add.sh --tmdb-id 693134
   → JSON con película creada
```

### Verificar que las descargas estén funcionando

```
sonarr-queue-list.sh
radarr-queue-list.sh
```