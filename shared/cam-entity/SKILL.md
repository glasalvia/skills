---
name: "cam-entity"
description: "Protocolo para capturar, guardar y analizar instantáneas desde cámaras de Home Assistant."
---

# Skill: Cam Snapshot
Procedimiento para capturar, guardar y analizar imágenes de una cámara de Home Assistant.

## Ejecución
1. **Entorno:** Asegurarse de estar en `/home/glasalvia/.openclaw/workspace`.
2. **Autenticación:** Obtener el token de HA **según el nodo** (ver `## Environment`; p. ej. en `fedora` la variable de entorno `HOME_ASSISTANT_KEY`; en otros nodos puede estar en `TOOLS.md`).
   ⚠️ **No escribir el token inline en el comando.** El redactor de secretos puede corromper el header `Authorization` y devolver `401 Unauthorized`. Volcarlo a un archivo temporal y leerlo desde ahí:
   `printf '%s' "$TOKEN_HA" > /tmp/ha_tok && chmod 600 /tmp/ha_tok`  (reemplazar `$TOKEN_HA` por la fuente del nodo)
   y usar `$(cat /tmp/ha_tok)` como valor del header. Borrar el temporal al terminar.
3. **Pasos:**
   - **Discovery:** Encontrar el `entity_id` de la cámara con:
     `curl -s -H "Authorization: Bearer $(cat /tmp/ha_tok)" http://192.168.1.65:8123/api/states | jq '.[] | select(.entity_id | startswith("camera."))'`
   - **Fetch:** Guardar la imagen con:
     `curl -s -H "Authorization: Bearer $(cat /tmp/ha_tok)" "http://192.168.1.65:8123/api/camera_proxy/<entity_id>" -o /home/glasalvia/.openclaw/workspace/camera_snapshot.jpg`
     Si devuelve **500**, suele ser **transitorio** (integración ONVIF/Tapo reiniciando). Reintentar una vez antes de concluir fallo.
   - **Adjuntar:** Adjuntar la imagen al usuario con `MEDIA:/home/glasalvia/.openclaw/workspace/camera_snapshot.jpg` ANTES de realizar cualquier otra acción.
   - **Describir:** Describir el contenido visible en la imagen (personas, objetos, ambiente, iluminación, actividad).

   > ⚠️ **NO eliminar el archivo.** La imagen debe permanecer disponible para el usuario. No ejecutar `rm` ni ninguna acción de limpieza sobre `camera_snapshot.jpg`.

## Environment
- **fedora:** Cliente HTTP contra HA en Raspi (`http://192.168.1.65:8123`). Token HA en la variable de entorno `HOME_ASSISTANT_KEY`. Captura snapshot de cámara Tapo.
- **Raspi:** Servidor HA local con integración Tapo. Token HA en su propia fuente del nodo (posiblemente `TOOLS.md`). Sin necesidad de fetch externo.
- **Dependencias HA:** `curl`, `jq`.
