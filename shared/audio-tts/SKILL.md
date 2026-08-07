---
name: "audio-tts"
description: "Skill para unificar el envío de notificaciones de audio TTS a dispositivos Google Home y Alexa (vía Home Assistant)."
---

# Skill: Audio Notify
Protocolo unificado para enviar notificaciones de audio (TTS) a dispositivos del hogar mediante un único punto de entrada lógico.

## Entorno y Requisitos
*   **Workspace:** `/home/glasalvia/.openclaw/workspace`
*   **Virtual environment:** `venvs/tts_env/bin/python` (no `tts_env/bin/python`)
*   **Dependencias:** `pychromecast`, `edge-tts`, `ffmpeg` (instaladas en el venv)
*   **Token HA:** Configurado en `TOOLS.md`

## Procedimiento de Ejecución

### 1. Google Home (Oficina, Dormitorio)
Requiere el entorno virtual `venvs/tts_env`.
- **Servicio:** `scripts/tts_oficina.py` (edge-tts → ffmpeg → pychromecast)
- **Dispositivos:** `Oficina` (192.168.1.60), `Dormitorio` (192.168.1.62)
- **Comando:**
  `bash -c "cd /home/glasalvia/.openclaw/workspace && source venvs/tts_env/bin/activate && python scripts/tts_oficina.py '<Nombre_Dispositivo>' '<Mensaje>'"`

### 2. Alexa (Dragon, Buho)
Requiere invocar el servicio de notificación de Home Assistant via API REST.
- **Entidades:** `notify.alexa_media_alexa_dragon`, `notify.alexa_media_2o_echo_dot_de_gonzalo` (Buho)
- **Alternativas:** `notify.alexa_media_en_todas_partes` (anuncio global)
- **Comando (Curl):**
  `curl -s -X POST -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d '{"message":"<Mensaje>"}' http://192.168.1.65:8123/api/services/notify/alexa_media_<entity_name>`

### 3. Google Home via Home Assistant (fallback)
Si el script de pychromecast falla, usar el servicio TTS de HA:
- **Endpoint:** `POST /api/services/tts/cloud_say`
- **Payload:** `{"entity_id":"media_player.<entidad>","message":"<Mensaje>"}`
- **Entidades:** `media_player.oficina`, `media_player.googlehome8344`, `media_player.tele_dormitorio`

## Flujo de Trabajo Sugerido para el Agente
1. Identificar el dispositivo de destino.
2. Verificar que el token de HA está disponible (TOOLS.md).
3. Si el destino es Google Home → ejecutar script con el venv de `venvs/tts_env`.
4. Verificar que `edge-tts` responde y el Chromecast se encuentra en la red.
5. Si el destino es Alexa → POST a HA con `notify.alexa_<nombre>_hablar`.
6. Validar resultado: Google Home → estado `PLAYING` en los logs; Alexa → código 200/201.
## Environment
- **cachy-gla:** TTS via `scripts/tts_oficina.py`. Dispositivos: Oficina (192.168.1.60), Dormitorio (192.168.1.62). Cliente HTTP directo a Google Home Mini.
- **Raspi:** TTS via Home Assistant `notify.google_assistant_sdk` o `notify.alexa_media`.
- **Hostname check:** `uname -n` para determinar script/endpoint.
