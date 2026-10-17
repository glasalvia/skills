---
name: "raspi-a2a-bridge"
description: "Comunicación bidireccional con Raspberry Pi vía A2A: control HA, WhatsApp, monitoreo, scripts, cámara, TTS."
---

# Skill: raspi-a2a-bridge — Integración A2A con Agente Remoto (Patrón General)

## Propósito
Establecer comunicación bidireccional entre este agente (fedora) y un agente remoto (Raspi, en Raspberry Pi 5) mediante el protocolo A2A Gateway Plugin, permitiendo ejecutar tareas, consultar estado y controlar dispositivos en el entorno del agente remoto.

Este skill describe el **patrón de integración**, no una configuración específica. Las variables concretas (IPs, puertos, tokens) se resuelven desde la configuración de A2A Gateway.

## Arquitectura

```
fedora    ──A2A (HTTP/JSON-RPC)──► Raspi (RPi 5)
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

## Environment: fedora ↔ Raspi (estado verificado 2026-10-17)

| Elemento | fedora (192.168.1.75) | Raspi (192.168.1.65) |
|---|---|---|
| Plugin | `~/.openclaw/workspace/plugins/a2a-gateway` (v1.5.1, ESM/TS) | mismo path, v1.5.1 |
| Puerto A2A | 18800 (`0.0.0.0`) | 18800 (`0.0.0.0`) |
| Alias del peer | `raspberry-pi` → `http://192.168.1.65:18800` | `fedora` → `http://192.168.1.75:18800` |
| `routing.defaultAgentId` | `el-arquitecto` | `main` |
| Token de entrada | en `openclaw.json → plugins.entries.a2a-gateway.config.security.token` | ídem |
| Store de peers | `~/.openclaw/a2a-peers.json` | ídem |

**Asimetría crítica:** el `defaultAgentId` **no** se copia entre nodos. Copiar `main` a fedora hace fallar todo task entrante con `invalid agent params: unknown agent id "main"`. El id válido en fedora es `el-arquitecto`.

Los tokens ya existen y están alineados: el token de entrada de un nodo es el token que el otro usa en su peers file. Nunca se imprimen; se verifican con `sed` redactado o por longitud.

## Prerrequisitos (Patrón)

- **A2A Gateway Plugin** instalado en **ambos** gateways (local y remoto)
- Puerto A2A (18800) abierto bidireccionalmente entre gateways
- Autenticación bearer mutua con tokens
- Peers configurados: cada gateway conoce al otro como peer
- Archivo `~/.openclaw/a2a-peers.json` con alias para resolver URL + token

### ⚠️ Regla de Tokens (Crítica)

El archivo `~/.openclaw/a2a-peers.json` del **ORIGEN** debe contener el **token del DESTINO**, no el propio.

**Explicación:** Cuando el gateway A del origen envía un mensaje al peer B, el mensaje incluye un token bearer. El gateway B valida ese token entrante contra su `security.inboundAuth.token`. Por lo tanto:

- `a2a-peers.json` en fedora → peer `raspberry-pi` → debe usar el token de Raspi
- `a2a-peers.json` en Raspi → peer `fedora` → debe usar el token de fedora

**Verificación empírica:** Si el origen envía su propio token, el destino responde con `-32603: Unauthorized: invalid or missing bearer token`.

```json
// a2a-peers.json en FEDORA (origen)
{
    "raspberry-pi": {
        "url": "http://192.168.1.65:18800",
        "token": "<TOKEN_DE_RASPI>"  // ← token del DESTINO, no el propio
    }
}
```

### Instalación del Plugin A2A en un Nodo Remoto

El plugin `a2a-gateway` vive en `workspace/plugins/a2a-gateway/`. Para instalarlo en un nodo remoto:

```bash
# Verificar que el plugin existe en el workspace del remoto
openclaw plugins install -l /home/glasalvia/.openclaw/workspace/plugins/a2a-gateway
# Reiniciar el gateway
systemctl --user restart openclaw-gateway
# Verificar que está escuchando
ss -tlnp | grep 18800
```

**⚠️ Caveat:** `openclaw doctor --fix` elimina entradas de plugins no registradas en el índice SQLite. Después de ejecutar `doctor --fix`, reinstalar el plugin A2A con el comando arriba.

El plugin es TypeScript (`index.ts`) sin compilado JS. `openclaw plugins install` lo acepta como "source checkout" (fallback TypeScript para paths de desarrollo local). No es necesario compilarlo.

## Protocolo de Comunicación

### Envío de mensaje A2A (comando genérico)
```bash
node <RUTA_PLUGIN>/skill/scripts/a2a-send.mjs \
  --peer raspberry-pi \
  --message "<INSTRUCCIÓN>" \
  --wait --timeout-ms <TIMEOUT_MS>
```

- `<RUTA_PLUGIN>`: `/home/glasalvia/.openclaw/workspace/plugins/a2a-gateway`
- `<ALIAS_PEER>`: alias definido en `~/.openclaw/a2a-peers.json`. En fedora el alias de la Raspi es `raspberry-pi`; en la Raspi el de fedora es `fedora`. Resuelve URL + token automáticamente.
- `--wait`: espera respuesta del agente remoto (bloqueante)
- `--timeout-ms`: 30000 para consultas simples, 120000 para tareas pesadas (scripts, Docker)

**Nota sobre `--agent-id`:** El script acepta `--agent-id <ID>` pero el agente que recibe el mensaje lo determina `routing.defaultAgentId` en la configuración del plugin del nodo destino, no este flag. El flag solo es útil para enviar a agentes alternativos si el soporte multi-agente está configurado explícitamente. Por defecto, omitirlo produce el mismo comportamiento. Verificado: en fedora el valor correcto es `el-arquitecto`; `main` solo existe en la Raspi.

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
  --wait --timeout-ms 30000
```
El agente remoto ejecuta los comandos vía `exec` y devuelve stdout como texto.

### Vector Acción — Script remoto
```bash
node a2a-send.mjs --peer <ALIAS> \
  --message "Ejecutá: python3 <RUTA_SCRIPT>" \
  --wait --timeout-ms 120000
```

### Vector Comunicación — Enviar mensaje a canal externo
```bash
node a2a-send.mjs --peer <ALIAS> \
  --message "Ejecutá: openclaw message send --channel <CANAL> --target '<DESTINO>' -m '<TEXTO>'" \
  --wait --timeout-ms 60000
```
**Importante:** No usar `sessions_send` para delivery a canales externos. Usar `exec` + `openclaw message send`.

### Vector API — Consultar servicio HTTP en remoto
```bash
node a2a-send.mjs --peer <ALIAS> \
  --message "Ejecutá: curl -s <URL_API> (con auth si corresponde)" \
  --wait --timeout-ms 30000
```

## Capacidades del Entorno Remoto (Raspi / Raspberry Pi 5)
*Esta sección describe lo que el agente remoto puede hacer, sin depender de IPs/tokens específicos.*

### Skills canónicos disponibles en el ecosistema unificado
| Skill canónico | Propósito | Agentes |
|---|---|---|
| `audio-tts` | TTS a Google Home y Alexa | fedora + Raspi |
| `cam-entity` | Captura de snapshots de cámaras | fedora + Raspi |
| `gog-workspace` | Google Workspace (Gmail, Calendar, Drive, Sheets) | fedora + Raspi |
| `home-assistant` | Control de IoT vía HA API | Raspi |
| `whatsapp` | Mensajería WhatsApp | Raspi |
| `raspi-a2a-bridge` | Integración A2A entre agentes | fedora |
| `raspberry-bridge` | Fallback SSH a RPi (contingencia) | fedora |

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

### Protocolo de Diagnóstico (ordenado por probabilidad de fallo)

Si un envío A2A falla, seguir esta secuencia:

1. **Verificar que el plugin A2A está escuchando en el peer:**
   ```bash
   curl -s -o /dev/null -w "%{http_code}" http://<PEER_IP>:18800/.well-known/agent-card.json
   # 200 = OK, 000 = conexión rechazada (plugin caído)
   ```

2. **Verificar que el plugin está instalado en el peer:**
   ```bash
   # En el peer remoto:
   openclaw plugins list --enabled | grep a2a-gateway
   ss -tlnp | grep 18800
   ```
   Si el plugin no aparece, reinstalar:
   ```bash
   openclaw plugins install -l /home/glasalvia/.openclaw/workspace/plugins/a2a-gateway
   systemctl --user restart openclaw-gateway
   ```

3. **Verificar que ambos gateways estén corriendo:** `openclaw gateway status`

4. **Verificar tokens:** Revisar que `a2a-peers.json` en el origen tenga el token del destino, no el propio.

5. **Revisar logs de auditoría del peer:**
   ```bash
   cat /home/glasalvia/.openclaw/a2a-audit.jsonl | grep -i "rejected\|error\|unauthorized"
   ```

6. **Revisar logs del gateway del peer:**
   ```bash
   grep -i "a2a\|unauthorized\|token" /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log
   ```

7. **Probar conectividad básica:**
   ```bash
   node a2a-send.mjs --peer <ALIAS> --message "Ejecutá hostname" --wait --timeout-ms 30000
   ```

### Archivos de diagnóstico
- **Logs de auditoría A2A (remoto):** `~/.openclaw/a2a-audit.jsonl`
- **Tareas completadas (remoto):** `~/.openclaw/a2a-tasks/<TASK_ID>.json`
- **Logs del gateway (remoto):** `/tmp/openclaw/openclaw-$(date +%Y-%m-%d).log`
- **Config del plugin (remoto):** `openclaw.json → plugins.entries.a2a-gateway`
