# Skill: actualizar-pasos

Sincroniza el último valor diario del sensor `sensor.celu_gon_daily_steps` de Home Assistant hacia una planilla de Google Sheets, agrupando un registro por día (fecha ART).

## Propósito

Registrar automáticamente los pasos acumulados del día antes del reseteo del sensor a medianoche, manteniendo un histórico consolidado en una planilla compartida.

## Requisitos

- Python 3.8+
- `gog` CLI autenticado (cuenta: `raspilasalvia@gmail.com`)
- Home Assistant reachable en `http://192.168.1.65:8123`
- Token HA con acceso a `/api/states/`
- Variables de entorno `GOG_KEYRING_PASSWORD` y `GOG_ACCOUNT` (el script las setea por defecto en `os.environ.setdefault()`; no requiere exportarlas manualmente)

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `actualizar.py` | Script principal de sincronización |
| `SKILL.md` | Este documento |

## Spreadsheet destino

- Nombre: **Actividad Fisica - Historial**
- ID: `1Pc_10GrPRC7FkfskIMBisIRps3uT72hLo5UzHDQ2Jfk`
- Hoja: **Actividad Fisica - Historial** (columnas: Fecha | Cantidad)

## Uso

```bash
# Ejecución normal (consulta HA y registra)
python3 actualizar.py

# Dry-run (simula sin escribir)
python3 actualizar.py --dry-run

# Forzar fecha específica (útil para tests)
python3 actualizar.py --fecha 2026-08-29
```

## Pipeline

1. `curl` a `{HA_URL}/api/states/sensor.celu_gon_daily_steps`
2. Extrae `state` (pasos) y `last_updated` (UTC)
3. Convierte `last_updated` a `America/Buenos_Aires` → fecha ART
4. `gog sheets get` columna A → verifica si la fecha ya existe
5. Si no existe: `gog sheets append` con `[fecha, pasos]`

### Nota técnica

El flag `--insert=INSERT_ROWS` es crítico: evita que `gog sheets append` sobrescriba filas existentes cuando la planilla tiene formato de **tabla estructurada** (Google Sheets convierte rangos a tabla automáticamente). Sin este flag, el append se comporta como OVERWRITE y puede eliminar registros previos.

## Logs

Todos los intentos se registran en `/tmp/pasos_cron.log` con timestamp ART.

## Cron recomendado

```cron
45 23 * * * cd /home/glasalvia/skills/shared/actualizar-pasos && python3 actualizar.py >> /tmp/pasos_cron.log 2>&1
```

Ejecuta 15 minutos antes del reseteo del sensor (00:00 ART).

## Mantenimiento

Si el spreadsheet ID cambia, actualizar `SPREADSHEET_ID` en `actualizar.py`.
Si el token HA se regenera, actualizar `HA_TOKEN` en `actualizar.py`.