---
name: "raspi-a2a-client"
description: "Comunicación A2A desde Raspi hacia cachy-gla: comandos remotos, búsqueda web, procesamiento."
---

# Skill: raspi-a2a-client — Cliente A2A hacia cachy-gla

## Propósito
Permitir que el Raspi envíe mensajes A2A a cachy-gla para ejecutar tareas que cachy-gla puede hacer y el Raspi no: búsqueda web, procesamiento intensivo, consultas a APIs externas, scraping, etc.

## Arquitectura

```
Raspi ──A2A (HTTP/JSON-RPC)──► cachy-gla (192.168.1.71)
  │                                  │
  │   web_search / web_fetch         │
  │   exec (procesamiento)           │
  │   tavily_search / tavily_extract  │
  │   Sesiones spawn (paralelo)      │
```

## Prerrequisitos

- Plugin A2A Gateway instalado en Raspi (verificado: sí, puerto 18800)
- Peer `cachy-gla` configurado en `~/.openclaw/a2a-peers.json` (verificado: sí)
- Token inbound de cachy-gla (`3dd4bb18...`) configurado en `a2a-peers.json` del Raspi para outbound (verificado: sí)

## ⚠️ Regla de Tokens

El `a2a-peers.json` del **ORIGEN** debe contener el token del **DESTINO**, no el propio.

- Raspi → cachy-gla: usar token de cachy-gla (`3dd4bb18...`)
- cachy-gla → Raspi: usar token de Raspi (`c3974bba...`)

## Protocolo de Comunicación

### Envío de mensaje A2A (comando genérico)
```bash
node <RUTA_PLUGIN>/skill/scripts/a2a-send.mjs \
  --peer cachy-gla \
  --message "<INSTRUCCIÓN>" \
  --wait --timeout-ms <TIMEOUT_MS>
```

- `<RUTA_PLUGIN>`: `/home/glasalvia/.openclaw/workspace/plugins/a2a-gateway`
- `--peer cachy-gla`: alias resuelto desde `~/.openclaw/a2a-peers.json`
- `--wait`: espera respuesta (bloqueante)
- `--timeout-ms`: 30000 consultas simples, 120000 tareas pesadas

### Nota sobre `--agent-id`
El flag `--agent-id main` es implícito. El agente que procesa el mensaje lo determina `routing.defaultAgentId` en la configuración del plugin del destino. No es necesario incluirlo a menos que haya multi-agente configurado explícitamente.

## Lo que cachy-gla puede ejecutar vía A2A

cachy-gla opera en un `agentTurn` aislado con herramientas completas:

| Herramienta | Propósito para el Raspi |
|---|---|
| `web_search` | Buscar información actualizada en la web |
| `web_fetch` | Extraer contenido de URLs |
| `tavily_search` | Búsqueda web avanzada con resúmenes AI |
| `tavily_extract` | Extraer contenido de páginas JS-render |
| `exec` | Ejecutar scripts o comandos (potencia de cachy-gla: 24 cores, 30GB RAM) |
| `sessions_spawn` | Procesamiento paralelo en sub-agentes |
| `read` / `write` / `edit` | Solo sobre su propio workspace (no accede al del Raspi) |
| `image` | Análisis de imágenes vía modelo de visión |

### Lo que cachy-gla NO puede hacer por el Raspi
- Acceder al filesystem del Raspi (solo vía SSH directo)
- Enviar mensajes a canales externos (WhatsApp, Telegram) — `message` tool no está disponible en contexto A2A
- Controlar Home Assistant del Raspi

## Vectores de Operación

### Vector Búsqueda Web
```bash
node a2a-send.mjs --peer cachy-gla \
  --message "Buscá en la web: <consulta> y devolvé un resumen con fuentes" \
  --wait --timeout-ms 60000
```

### Vector Extraer URL
```bash
node a2a-send.mjs --peer cachy-gla \
  --message "Extraé el contenido de <URL> y devolvé el texto principal" \
  --wait --timeout-ms 60000
```

### Vector Procesamiento (scripts pesados)
```bash
node a2a-send.mjs --peer cachy-gla \
  --message "Ejecutá: python3 <SCRIPT>" \
  --wait --timeout-ms 120000
```

### Vector Consulta de Estado
```bash
node a2a-send.mjs --peer cachy-gla \
  --message "Ejecutá: free -h; uptime; echo '---'; openclaw status | head -10" \
  --wait --timeout-ms 30000
```

## Limitaciones Conocidas

1. **Sin `message` tool en contexto A2A**: cachy-gla no puede enviar a WhatsApp/Telegram desde una sesión A2A. Usar `exec` + `openclaw message send` como workaround.
2. **Sin acceso a filesystem local**: cachy-gla solo ve su propio workspace. No puede leer archivos del Raspi vía A2A.
3. **Timeout de tareas largas**: Scripts >2 min requieren aumentar `--timeout-ms` o usar `--non-blocking`.

## Mantenimiento

- Si un envío A2A falla, verificar puerto 18800 escuchando en cachy-gla
- Verificar que `a2a-peers.json` tenga el token correcto del destino
- Logs de auditoría A2A: `~/.openclaw/a2a-audit.jsonl`
- El plugin debe estar instalado: `openclaw plugins list --enabled | grep a2a-gateway`