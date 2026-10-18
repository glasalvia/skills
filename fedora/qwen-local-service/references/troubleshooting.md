# Fallos conocidos y su firma

## El puerto responde pero el modelo no

**Firma:** `status` devuelve `loading`; `curl /v1/models` vacío o error.
**Causa:** el proceso arrancó y aún carga pesos desde NVMe. `active (running)` no significa listo.
**Acción:** esperar con `start` (que ya espera) o mirar `logs --since "2 min ago"`. `TimeoutStartSec=300` es el techo de systemd.

## Alias distinto

**Firma:** `doctor` → `alias distinto: servidor publica '<ruta>.gguf'`.
**Causa:** falta `--alias` o no coincide con el `id` registrado en OpenClaw.
**Acción:** corregir `ExecStart` y `daemon-reload`; después `restart`.

## Dos dueños del proceso

**Firma:** `doctor` → `llama-server huérfano(s): <pid>`; o el servicio queda `active` pero el puerto lo responde otra instancia.
**Causa:** se lanzó `nohup`/script manual mientras la unidad existía. `Restart=on-failure` relanza la unidad y compiten por el puerto; la instancia nueva muere sin error visible.
**Acción:** matar el huérfano, `systemctl --user restart`, y no volver a arrancar fuera de systemd.

## Respuesta vacía con `finish_reason: length`

**Firma:** `content` vacío, todo el texto en `reasoning_content`.
**Causa:** el modelo piensa por defecto y `max_tokens` se agota antes del contenido.
**Acción:** `chat_template_kwargs: {"enable_thinking": false}`. Medido: 38 tokens frente a 384 para la misma decisión.

## El probe del proveedor falla aunque la inferencia responda

**Firma:** "The connection probe failed" en OpenClaw; `curl` funciona.
**Causa:** el probe usa 8 tokens y exige respuesta visible; con thinking activo `content` viene vacío.
**Acción:** no perseguir la red. Verificar con `probe` (real), tool call y `models.list` con `view: "configured"`.

## Degradación silenciosa de velocidad

**Firma:** tok/s cae a la mitad sin errores; `doctor` muestra RAM disponible baja.
**Causa:** el SO evicta páginas de expertos MoE; llama.cpp relee del NVMe en cada token.
**Acción:** dejar ≥2 GiB de RAM libre, bajar `--n-cpu-moe`, o pasar a una cuantización menor (`IQ4_XS`).

## Dispatch rechazado por sandbox

**Firma:** `target agent is not sandboxed for this restricted Workboard card.`
**Causa:** el caller aporta autoridad restringida y el worker no está en sandbox Docker.
**Acción:** `openclaw workboard dispatch --admin`. Es el modo documentado para host completo; `qwen-ctl.sh dispatch` ya lo usa.

## Tarjeta `running` que nunca cierra

**Firma:** estado `running` más allá de `maxRuntimeSeconds`; sin heartbeat.
**Causa:** worker colgado, modelo sin respuesta, o dos workers compitiendo por la única ranura.
**Acción:** `openclaw workboard dispatch` hace limpieza de claims vencidos; si persiste, `workboard_reclaim` y revisar `logs`.

## Reinicio durante inferencia

**Firma:** worker bloqueado a mitad de tarjeta tras un `restart`.
**Causa:** `stop` mata la conexión en vuelo.
**Acción:** `restart` ya se niega si hay conexiones establecidas. Usar `--force` sólo con la tarjeta bloqueada a mano.
