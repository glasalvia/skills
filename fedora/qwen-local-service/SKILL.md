---
name: qwen-local-service
description: Operar el servidor local llama.cpp/Qwen de este nodo — verificar readiness real, levantar y detener el servicio systemd, leer logs, medir tok/s, diagnosticar VRAM y deriva, y crear/despachar/verificar tareas del Merovingio en Workboard.
---

# Servicio Qwen local — ciclo de vida y despacho

## Cuándo usar

- Saber si el servidor local está arriba **y** listo para inferir (no alcanza con el puerto abierto).
- Levantarlo, detenerlo o reiniciarlo sin duplicar procesos.
- Leer sus logs sin colgar la sesión.
- Medir rendimiento real (prefill y decode) tras un cambio de flags.
- Diagnosticar por qué el modelo no responde, no aparece en el picker o murió solo.
- Asignarle una tarea al Merovingio y verificar su resultado.

## Contrato

- **Una sola fuente de verdad:** la unidad systemd de usuario `llama-qwen.service`. Este script nunca lanza `llama-server` por su cuenta; siempre delega en `systemctl --user`.
- **Idempotencia:** `start` sobre un servicio ya listo no hace nada y retorna 0.
- **Readiness ≠ liveness:** `ready` exige que `/v1/models` devuelva el alias configurado. `active (running)` no alcanza.
- **Un solo trabajo de inferencia:** el servidor corre con `--parallel 1`. Las ramas pesadas toman un lock y rechazan la segunda invocación.
- **El resultado se prueba:** `verify` re-ejecuta la evidencia declarada y compara salidas. Un `proof` autodeclarado no se acepta como verdad.

## Procedimiento

1. **Diagnosticar antes de tocar.**
   `scripts/qwen-ctl.sh status`
   Criterio: código 0 = `ready`; 1 = detenido; 2 = cargando o puerto ajeno. No se continúa con `start` sin saber cuál de los tres es.

2. **Levantar si hace falta.**
   `scripts/qwen-ctl.sh start`
   Criterio: retorna 0 solo cuando el alias responde en `/v1/models`. Si expira, imprime el journal y retorna 1.
   Guardas: rechaza si hay un `llama-server` huérfano fuera del cgroup de la unidad, o si otro proceso ocupa más de 2 GiB de VRAM (salvo `--force`).

3. **Leer logs sin bloquear.**
   `scripts/qwen-ctl.sh logs --since "30 min ago"` (por defecto, últimas 100 líneas)
   `--follow` solo cuando el humano lo pida explícitamente.

4. **Detener o reiniciar con verificación.**
   `scripts/qwen-ctl.sh stop` — espera y confirma que el puerto quedó libre.
   `scripts/qwen-ctl.sh restart` — se niega si hay conexiones establecidas contra el puerto (inferencia en vuelo).

5. **Medir.**
   `scripts/qwen-ctl.sh probe`
   Criterio: imprime `prompt_per_second` y `predicted_per_second` leídos del campo `timings` de la respuesta, y apenda la serie en `~/.local/state/qwen-local/metrics.csv`. Nunca cronometrar a mano.

6. **Diagnóstico integral.**
   `scripts/qwen-ctl.sh doctor`
   Criterio: unidades, linger, alias, huérfanos, VRAM, RAM, deriva de flags y registro del proveedor. Retorna 1 si hay un fallo crítico.

7. **Asignar trabajo al Merovingio.**
   `scripts/qwen-ctl.sh task --title "<título>" --notes-file <archivo> [--agent el-merovingio] [--board default]`
   Criterio: crea la tarjeta en `ready`, arranca el servicio si está caído, despacha con `--admin` y espera el cierre.

8. **Verificar el resultado.**
   `scripts/qwen-ctl.sh verify --card <id>`
   Criterio: relee el artefacto, valida el contrato de salida y **re-ejecuta** cada `evidence[].cmd`, comparando la salida. Cualquier divergencia retorna 1.

## Verificación de la propia skill

`scripts/qwen-ctl.sh selftest` ejecuta `status`, `probe` y `doctor` contra el servicio real. Una skill que no se prueba a sí misma se degrada en cada edición.

## Referencias

- `references/service.md` — unidad, flags, perfiles de contexto por drop-in, política de arranque.
- `references/troubleshooting.md` — firmas de fallo conocidas y su causa.
- `assets/llama-qwen.service` — plantilla de la unidad para reconstruirla.
- Skills relacionadas: `local-inference-openclaw` (dimensionar y registrar el modelo), `local-worker-agent` (crear el agente trabajador).
