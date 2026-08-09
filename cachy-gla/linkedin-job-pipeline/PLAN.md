# Plan: linkedin-pipeline — Recolección autónoma vía Raspi

## Ecuación

El pipeline LinkedIn en cachy-gla no se ejecuta porque el host no está disponible 24/7 →
El Raspi (192.168.1.65) está disponible 24/7 con gog (linuxbrew) y openclaw CLI →
Las alertas LinkedIn se reenvían de glasalviacalio@gmail.com a raspilasalvia@gmail.com →
**Solución:** Transferir ejecución del pipeline al Raspi, con notificación WhatsApp diaria.

## Restricciones

- Qwen (Ollama) solo disponible en cachy-gla → toda edición de código se hace aquí, luego se sincroniza
- Raspi usa deepseek-v4-flash como modelo de agente
- El cron existente `check_emails_daily` (09:00/18:00 ART) envía resumen WhatsApp
- Los scripts pipeline son Python puro — no requieren agente para ejecutarse

## Tareas

| # | Tarea | Depende de | Complejidad | Modelo | Archivos involucrados |
|---|-------|-----------|-------------|--------|----------------------|
| 1 | Corregir profile.yaml con parámetros reales | — | baja | qwen_mtp | `profile.yaml` |
| 2 | Agregar language_filter + recalibrar scorings en profile_matcher.py | 1 | media | qwen_mtp | `profile_matcher.py` |
| 3 | Crear linkedin_digest_export.py (consulta DB → texto plano) | — | baja | qwen_mtp | `linkedin_digest_export.py` (nuevo) |
| 4 | Crear weekly_scrape.sh (loop scraping semanal) | — | baja | qwen_mtp | `weekly_scrape.sh` (nuevo) |
| 5 | Sincronizar cambios al Raspi vía git + deploy | 1,2,3,4 | baja | main | — |
| 6 | Instalar gog en PATH del Raspi (symlink linuxbrew → /usr/local/bin) | 5 | baja | main | — |
| 7 | Configurar system crontab en Raspi (pipeline 08:45/17:45 + scraping sábados) | 5,6 | baja | main | crontab del Raspi |
| 8 | Crear wrapper script Raspi para envío WhatsApp del digest | 5 | baja | qwen_mtp | `linkedin_whatsapp_notify.sh` (nuevo, en Raspi) |
| 9 | Agregar cron OpenClaw linkedin_digest en Raspi | 8 | baja | main | cron jobs del Raspi |
| 10 | Scoring forzado inicial (176 ofertas) | 7 | baja | main | — |
| 11 | Verificación E2E | 9,10 | media | main | — |

## Verificación final

```bash
# En el Raspi:
cd ~/.openclaw/workspace/skills/linkedin-job-pipeline
python3 db_setup.py  # debe mostrar stats
python3 profile_matcher.py --list-top 10  # debe mostrar scores
# El cron debe haberse ejecutado sin errores:
cat /tmp/linkedin_cron.log | tail -20
# Debe haber llegado un WhatsApp con el digest
```