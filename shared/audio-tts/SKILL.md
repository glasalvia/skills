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
*   **ElevenLabs API Key:** Almacenada en secrets store como `ELEVENLABS` — se resuelve automáticamente desde `scripts/tts_elevenlabs.py`

## Procedimiento de Ejecución

### 1. Google Home — Motor Edge-TTS (estándar)
Requiere el entorno virtual `venvs/tts_env`.
- **Servicio:** `scripts/tts_oficina.py` (edge-tts → ffmpeg → pychromecast)
- **Dispositivos:** `Oficina` (192.168.1.60), `Dormitorio` (192.168.1.62)
- **Comando:**
  `bash -c "cd /home/glasalvia/.openclaw/workspace && source venvs/tts_env/bin/activate && python scripts/tts_oficina.py '<Nombre_Dispositivo>' '<Mensaje>'"`

### 1b. Google Home — Motor ElevenLabs (alta fidelidad)
Requiere la API key de ElevenLabs en el secrets store (ver arriba).
- **Servicio:** `scripts/tts_elevenlabs.py` (ElevenLabs API → pychromecast — sin ffmpeg ni edge-tts)
- **Dispositivos:** `Oficina`, `Dormitorio`
- **Voz por defecto:** Martin Osborne (ID `W5JElH3dK1UYYAiHH7uh`, español peninsular — aprobada como "El Arquitecto")
- **Voces preconfiguradas:** `martin`, `elder`, `adam-dominant`, `leonidas`, `maicolangel`, `mordred`, `rachel`
- **Comando básico:**
  `python /home/glasalvia/.openclaw/workspace/scripts/tts_elevenlabs.py 'Oficina' 'Mensaje'`
- **Comando con voz y ajustes:**
  `python scripts/tts_elevenlabs.py 'Oficina' 'Mensaje' --voice elder --stability 0.25 --similarity 0.9 --style 0.6`
- **Nota:** Este script NO necesita el venv `tts_env`; solo requiere `curl` y `pychromecast` instalados en el sistema.

### 2a. Alexa — Motor Estándar
Requiere invocar el servicio de notificación de Home Assistant via API REST.
- **Entidades:** `notify.alexa_media_alexa_dragon`, `notify.alexa_media_2o_echo_dot_de_gonzalo` (Buho)
- **Alternativas:** `notify.alexa_media_en_todas_partes` (anuncio global)
- **Comando (Curl):**
  `curl -s -X POST -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d '{"message":"<Mensaje>"}' http://192.168.1.65:8123/api/services/notify/alexa_media_<entity_name>`

### 2b. Alexa — Motor ElevenLabs
El script `tts_elevenlabs.py` también soporta Alexa mediante el parámetro:
`python scripts/tts_elevenlabs.py 'Dragon' 'Mensaje'`
- **Entidades reconocidas:** `dragon` → `alexa_media_alexa_dragon`, `buho` → `alexa_media_2o_echo_dot_de_gonzalo`, `todas` → `alexa_media_en_todas_partes`
- **Nota:** ElevenLabs no aplica para Alexa como reemplazo del motor TTS de Alexa — el mensaje se entrega como texto. La voz de Alexa sigue siendo la estándar de Amazon.

### 3. Google Home via Home Assistant (fallback)
Si el script de pychromecast falla, usar el servicio TTS de HA:
- **Endpoint:** `POST /api/services/tts/cloud_say`
- **Payload:** `{"entity_id":"media_player.<entidad>","message":"<Mensaje>"}`
- **Entidades:** `media_player.oficina`, `media_player.googlehome8344`, `media_player.tele_dormitorio`

## Flujo de Trabajo Sugerido para el Agente
1. Identificar el dispositivo de destino.
2. Verificar los recursos disponibles:
   - `scripts/tts_oficina.py` → edge-tts (voz robótica, rápida, sin costo)
   - `scripts/tts_elevenlabs.py` → ElevenLabs (voz natural, alta fidelidad, requiere API key y créditos)
3. **Si se requiere máxima calidad de voz** (El Arquitecto, notificaciones importantes):
   → Usar `scripts/tts_elevenlabs.py` con la voz `martin` (por defecto) o la que se especifique.
4. **Si es una notificación rápida** (temporizadores, alertas simples):
   → Usar `scripts/tts_oficina.py` con edge-tts (menor latencia).
5. Si el destino es Google Home → ejecutar el script correspondiente.
6. Si el destino es Alexa → usar el script o curl directo a HA (la voz será la de Alexa, no ElevenLabs).
7. Validar resultado: Google Home → estado `PLAYING` en los logs; Alexa → código 200/201.
## Environment
- **cachy-gla:** TTS via `scripts/tts_oficina.py`. Dispositivos: Oficina (192.168.1.60), Dormitorio (192.168.1.62). Cliente HTTP directo a Google Home Mini.
- **Raspi:** TTS via Home Assistant `notify.google_assistant_sdk` o `notify.alexa_media`.
- **Hostname check:** `uname -n` para determinar script/endpoint.
