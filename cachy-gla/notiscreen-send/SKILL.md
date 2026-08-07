---
name: "notiscreen-send"
description: "Enviar notificaciones al dashboard claw-notifications del Turing Smart Screen vía notiscreen CLI o socket Unix."
---

# NotiScreen Send — Enviar notificaciones al dashboard claw-notifications

## Descripción
El dashboard `claw-notifications` corre en el Turing Smart Screen 3.5" (320×480 portrait, 180° rotado vía software). Acepta notificaciones vía Unix socket JSON o mediante el CLI `notiscreen`. Las notificaciones muestran un alien de Space Invaders en pantalla negra durante ~1.8s antes de desplegar la tarjeta de notificación.

## Requisitos previos
- El servicio `notiscreen.service` debe estar corriendo (`systemctl --user enable --now notiscreen.service`).
- Verificar con `notiscreen ping`.

## Método 1: CLI (recomendado)

```bash
# Notificación simple
notiscreen notify -t "Título" -l success

# Con cuerpo descriptivo
notiscreen notify -t "Título" -b "Descripción detallada del evento" -l warning -d 8

# Limpiar cola y restaurar dashboard
notiscreen clear
```

### Parámetros del subcomando `notify`
| Flag | Requerido | Default | Descripción |
|------|-----------|---------|-------------|
| `-t, --title` | Sí | — | Título (máx ~28 chars visibles) |
| `-b, --body` | No | `""` | Cuerpo con word-wrap automático |
| `-l, --level` | No | `info` | `info`, `success`, `warning`, `error` |
| `-d, --duration` | No | `5` | Segundos visibles |

### Colores por nivel
| Nivel | Color | Ícono |
|-------|-------|-------|
| `info` | Azul | ℹ |
| `success` | Verde | ✓ |
| `warning` | Naranja | ⚠ |
| `error` | Rojo | ✕ |

## Método 2: Socket Unix directo

```bash
echo '{"action":"notify","title":"Test","body":"Cuerpo","level":"success","duration":5}' | nc -U /tmp/notiscreen.sock
```

Protocolo JSON, una línea por comando, terminada en `\n`. Respuesta en el mismo formato.

### Acciones disponibles

**`notify`** — Enviar notificación
```json
{"action":"notify","title":"string","body":"string","level":"info|success|warning|error","duration":5.0}
```

**`ping`** — Verificar que el daemon responde
```json
{"action":"ping"}
```
Respuesta: `queue_size` + snapshot de métricas.

**`status`** — Estado completo
```json
{"action":"status"}
```

**`clear`** — Vaciar cola y restaurar dashboard
```json
{"action":"clear"}
```

## Manejo de errores
- **Daemon no corriendo:** `Cannot connect to daemon` → `systemctl --user start notiscreen.service`
- **Cola llena:** `Queue full` (máx 10) → esperar o `notiscreen clear`
- **Display desconectado:** `Restart=always`, reintenta cada 5s. Notificaciones enviadas sin display se pierden.

## Integración típica
```bash
# Build
make build && notiscreen notify -t "Build OK" -l success || notiscreen notify -t "Build FAIL" -b "$(tail -5 build.log)" -l error -d 10

# Cron
0 9 * * 1-5 notiscreen notify -t "Daily" -b "En 15 min" -l info -d 8

# Git hook
notiscreen notify -t "Push a main" -b "$(git log -1 --oneline)" -l info -d 4
```
