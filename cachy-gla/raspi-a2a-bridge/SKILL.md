---
name: "raspi-a2a-bridge"
description: "Comunicación bidireccional con Raspberry Pi vía A2A: control HA, WhatsApp, monitoreo, scripts, cámara, TTS."
---

# Skill: raspi-a2a-bridge — Integración A2A con Agente Remoto (Patrón General)

## Propósito
Establecer comunicación bidireccional entre este agente (cachy-gla) y un agente remoto (Raspi, en Raspberry Pi 5) mediante el protocolo A2A Gateway Plugin, permitiendo ejecutar tareas, consultar estado y controlar dispositivos en el entorno del agente remoto.

Este skill describe el **patrón de integración**, no una configuración específica. Las variables concretas (IPs, puertos, tokens) se resuelven desde la configuración de A2A Gateway.

## Arquitectura

```
cachy-gla ──A2A (HTTP/JSON-RPC)──► Raspi (RPi 5)
    │                                    │
    │  ┌─ Vectores de comando ──┐        │
    │  │  exec → comando shell  │        ├── Home Assistant API
    │  │  message → WhatsApp    │        ├── Servicios Docker
    │  │  consulta → estado     │        ├── Google Workspace
    │  └────────────────────────┘        ├── Scripts workspace
    │                                    ├── Dispositivos IoT
    │                                    ├── TTS (Alexa/Google Home)
    │                                    └── Cámara, sensores
```

## Prerrequisitos (Patrón)

- **A2A Gateway Plugin** instalado en **ambos** gateways (local y remoto)
- Puerto A2A (18800) abierto bidireccionalmente entre gateways
- Autenticación bearer mutua con tokens
- Peers configurados: cada gateway conoce al otro como peer
- Archivo `~/.openclaw/a2a-peers.json` con alias para resolver URL + token

## Protocolo de Comunicación

### Envío de mensaje A2A (comando genérico)
```bash
node <RUTA_PLUGIN>/skill/scripts/a2a-send.mjs \
  --peer <ALIAS_PEER> \
  --message "<INSTRUCCIÓN>" \
  --agent-id main \
  --wait --timeout-ms <TIMEOUT_MS>
```

- `<RUTA_PLUGIN>`: `/home/glasalvia/.openclaw/workspace/plugins/a2a-gateway`
- `<ALIAS_PEER>`: alias definido en `~/.openclaw/a2a-peers.json`
- `--wait`: espera respuesta del agente remoto (bloqueante)
- `--timeout-ms`: 30000 para consultas simples, 120000 para tareas pesadas (scripts, Docker)

### Lo que el agente remoto puede ejecutar
El agente remoto, al recibir una instrucción A2A, opera en un `agentTurn` aislado con las siguientes herramientas disponibles:
- `exec`: ejecutar comandos shell arbitrarios
- `sessions_send`: enviar mensajes inter-sesión (NO para envío a canales externos)
- `sessions_spawn`: crear sub-agentes para trabajo en paralelo
- `read`/`write`/`edit`: manipular archivos en su workspace
- `web_search`/`web_fetch`: buscar información web

**Restricción conocida:** La herramienta `message` (envío a canales como WhatsApp/Telegram) **no está disponible** en el contexto `agentTurn` de A2A. Para enviar mensajes a canales externos, usar `exec` con el CLI de OpenClaw: `openclaw message send --channel <CANAL> --target <DESTINO> -m "<TEXTO>"`.

## Vectores de Operación (Patrones)

### Vector Consulta — Estado del sistema remoto
```bash
node a2a-send.mjs --peer <ALIAS> \
  --message "Ejecutá: free -h; df -h /; uptime; echo '---'; docker ps --format '{{.Names}} {{.Status}}' | head -10" \
  --agent-id main --wait --timeout-ms 30000
```
El agente remoto ejecuta los comandos vía `exec` y devuelve stdout como texto.

### Vector Acción — Script remoto
```bash
node a2a-send.mjs --peer <ALIAS> \
  --message "Ejecutá: python3 <RUTA_SCRIPT>" \
  --agent-id main --wait --timeout-ms 120000
```

### Vector Comunicación — Enviar mensaje a canal externo
```bash
node a2a-send.mjs --peer <ALIAS> \
  --message "Ejecutá: openclaw message send --channel <CANAL> --target '<DESTINO>' -m '<TEXTO>'" \
  --agent-id main --wait --timeout-ms 60000
```
**Importante:** No usar `sessions_send` para delivery a canales externos. Usar `exec` + `openclaw message send`.

### Vector API — Consultar servicio HTTP en remoto
```bash
node a2a-send.mjs --peer <ALIAS> \
  --message "Ejecutá: curl -s <URL_API> (con auth si corresponde)" \
  --agent-id main --wait --timeout-ms 30000
```

## Capacidades del Entorno Remoto (Raspi / Raspberry Pi 5)
*Esta sección describe lo que el agente remoto puede hacer, sin depender de IPs/tokens específicos.*

### Skills canónicos disponibles en el ecosistema unificado
| Skill canónico | Propósito | Agentes |
|---|---|---|
| `audio-tts` | TTS a Google Home y Alexa | cachy-gla + Raspi |
| `cam-entity` | Captura de snapshots de cámaras | cachy-gla + Raspi |
| `gog-workspace` | Google Workspace (Gmail, Calendar, Drive, Sheets) | cachy-gla + Raspi |
| `home-assistant` | Control de IoT vía HA API | Raspi |
| `whatsapp` | Mensajería WhatsApp | Raspi |
| `raspi-a2a-bridge` | Integración A2A entre agentes | cachy-gla |
| `raspberry-bridge` | Fallback SSH a RPi (contingencia) | cachy-gla |

### Hardware
- Raspberry Pi 5, CPU ARM Cortex-A76 4 núcleos, 8 GB RAM
- Almacenamiento NVMe ~470 GB
- Red WiFi + Tailscale VPN

### Integraciones
| Sistema | Rol | Acceso |
|---|---|---|
| Home Assistant | Domótica: luces, clima, aspiradora, cámara, sensores | API REST local |
| Docker | Contenedores: HA, Sonarr, Radarr, Prowlarr, Bazarr, Valheim, Flaresolverr, FileBrowser | Docker CLI |
| Google Workspace | Gmail, Calendar, Drive, Sheets | gog CLI |
| Ollama | Modelos locales (llama3.2, tinyllama) | API localhost |
| Plex | Servidor multimedia | Localhost |
| TV/Chromecast/Alexa | Dispositivos de reproducción | API HTTP |
| Tavily/OpenRouter | Búsqueda web y LLMs externos | Provider config |

### Dispositivos IoT (vía Home Assistant)
- Cámara IP (Tapo C210/C220) con detección de movimiento/personas
- Luces WiFi (spots GU10, plafón, RGB, lámparas)
- Sensor de clima (temp, humedad desde Alexa)
- Aspiradora robot
- Split de aire acondicionado
- Tracking de personas (celulares, smartwatch)

### Scripts Disponibles en Workspace
- `scripts/trading/`: monitoreo de cripto y mercados financieros
- `scripts/ha_monitor/`: monitoreo y control de Home Assistant
- `scripts/noticias/`: agregación de RSS y noticias económicas
- `scripts/email/`: revisión de Gmail
- `scripts/utilidades/`: utilidades varias (dólar, imágenes, etc.)
- `scripts/tts_oficina.py`: síntesis de voz a Google Home/Alexa

### Sesiones de Chat
- WhatsApp (DM directo y grupos)
- Telegram (bot configurado)
- Webchat (Dashboard OpenClaw)
- Sesiones A2A (desde peers)

## Limitaciones Conocidas (Patrón)

1. **Sin `message` tool en contexto A2A**: El agente remoto no puede usar la herramienta `message` directamente en sesiones A2A. Como workaround, usar `exec` + `openclaw message send --channel <CANAL>`.
2. **Sin delivery externo vía `sessions_send`**: `sessions_send` solo inyecta texto en la sesión objetivo como mensaje inter-sesión; no gatilla envío al canal externo (WhatsApp, Telegram, etc.).
3. **Sin GPU para ML**: El agente remoto corre en ARM sin GPU dedicada — solo modelos pequeños vía Ollama.
4. **Sin exposición a internet**: Servicios accesibles solo por red local o Tailscale VPN.
5. **Sin modificaciones del sistema**: No modificar crontab, systemd, nginx, etc. sin inspeccionar estado previo.
6. **Sin comandos destructivos**: Preferir `trash` sobre `rm`; preguntar ante ambigüedad.
7. **Timeout de tareas largas**: Scripts que tomen >2 min requieren aumentar `--timeout-ms` o usar `--non-blocking` con consulta posterior.

## Mantenimiento de la Conexión

- Si un envío A2A falla, verificar:
  1. Que ambos gateways estén corriendo (`openclaw gateway status`)
  2. Que los puertos A2A (18800) estén abiertos (firewall UFW/nftables)
  3. Que los tokens no hayan rotado
  4. Que los peers estén configurados correctamente
- Para verificar conectividad:
```bash
node a2a-send.mjs --peer <ALIAS> --message "ping" --agent-id main --wait --timeout-ms 10000
```
- Los logs de auditoría A2A están en `~/.openclaw/a2a-audit.jsonl` en el gateway remoto
- Las tareas completadas se almacenan en `~/.openclaw/a2a-tasks/<TASK_ID>.json`
