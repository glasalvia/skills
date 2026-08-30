#!/usr/bin/env python3
"""
actualizar.py — Consulta Home Assistant (sensor.celu_gon_daily_steps)
y registra el último valor del día en Google Sheets (Actividad Fisica - Historial).

Uso:
    python3 actualizar.py                          # ejecución normal
    python3 actualizar.py --dry-run                # simula, no escribe
    python3 actualizar.py --fecha YYYY-MM-DD       # fuerza fecha específica (test)

Pre-requisitos:
    - gog CLI autenticado con cuenta raspilasalvia@gmail.com
    - GOG_KEYRING_PASSWORD y GOG_ACCOUNT configurados como env vars
    - Home Assistant accesible desde el nodo
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

# GOG_KEYRING_PASSWORD requerida fuera del entorno OpenClaw
os.environ.setdefault("GOG_KEYRING_PASSWORD", "Capicua1221")
os.environ.setdefault("GOG_ACCOUNT", "raspilasalvia@gmail.com")

# ─── Configuración ────────────────────────────────────────────────────────────

HA_URL = "http://192.168.1.65:8123"
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIxMDE1ZGYzZThlMWY0NTY3YTUwNjA1ZjY3ZjhlNDcyMSIsImlhdCI6MTc3MTA1MDEzMiwiZXhwIjoyMDg2NDEwMTMyfQ.3XwElC9j4xXa1Rl7rpMTW3mNpeI3UCD-g4RT8xylNHs"
SENSOR = "sensor.celu_gon_daily_steps"
SPREADSHEET_ID = "1Pc_10GrPRC7FkfskIMBisIRps3uT72hLo5UzHDQ2Jfk"
SHEET_NAME = "Actividad Fisica - Historial"
RANGE = f"'{SHEET_NAME}'!A:B"
TZ_ART = timezone(timedelta(hours=-3))
LOG_FILE = "/tmp/pasos_cron.log"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now(TZ_ART).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def consultar_ha():
    """Consulta el sensor en HA y devuelve (state, last_updated_utc)."""
    url = f"{HA_URL}/api/states/{SENSOR}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    state = int(float(data["state"]))
    last_updated_utc = data["last_updated"]  # ISO 8601
    return state, last_updated_utc


def consultar_ha_historial(fecha_art):
    """
    Consulta el historial de HA para una fecha ART específica.
    El sensor resetea a 0 a las 03:00 UTC (medianoche ART).
    Devuelve el último valor registrado antes del reseteo del día siguiente.
    """
    # Periodo: medianoche ART de la fecha (03:00 UTC) hasta la medianoche ART del día siguiente
    dt_fecha = datetime.strptime(fecha_art, "%Y-%m-%d").replace(tzinfo=TZ_ART)
    dt_inicio = dt_fecha.replace(hour=0, minute=0, second=0, microsecond=0)
    dt_fin = dt_inicio + timedelta(days=1)
    
    inicio_iso = dt_inicio.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    fin_iso = dt_fin.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    
    url = f"{HA_URL}/api/history/period/{inicio_iso}?filter_entity_id={SENSOR}&end_time={fin_iso}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    
    if not data or not data[0]:
        raise ValueError(f"Sin datos históricos para {fecha_art}")
    
    # Filtrar estados válidos (>0) y tomar el último
    estados = []
    for entry in data[0]:
        state_str = entry.get("state", "")
        try:
            val = int(float(state_str))
        except (ValueError, TypeError):
            continue
        estados.append((entry.get("last_updated", ""), val))
    
    if not estados:
        raise ValueError(f"Sin estados válidos en historial para {fecha_art}")
    
    # Tomar el último valor (antes del reseteo del día siguiente)
    last_state = estados[-1][1]
    log(f"Historial HA → último estado antes del reseteo: {last_state} (de {len(estados)} registros)")
    return last_state


def utc_to_art_date(iso_utc):
    """Convierte timestamp UTC a fecha ART (America/Buenos_Aires)."""
    dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    dt_art = dt.astimezone(TZ_ART)
    return dt_art.strftime("%Y-%m-%d")


def fecha_ya_existe(fecha):
    """Verifica si la fecha ya está registrada en la columna A de la planilla."""
    cmd = [
        "gog", "sheets", "get", SPREADSHEET_ID,
        f"'{SHEET_NAME}'!A:A",
        "--account=raspilasalvia@gmail.com",
        "--no-input", "--plain",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            log(f"ERROR consultando planilla: {result.stderr.strip()}")
            return False
        for line in result.stdout.strip().split("\n"):
            if line.strip() == fecha:
                return True
    except Exception as e:
        log(f"ERROR en verificación: {e}")
    return False


def append_a_planilla(fecha, pasos):
    """
    Append [fecha, pasos] a la planilla.
    gog sheets append usa pipe (|) como separador de celdas.
    """
    valores = f"{fecha}|{pasos}"
    cmd = [
        "gog", "sheets", "append", SPREADSHEET_ID,
        RANGE,
        valores,
        "--account=raspilasalvia@gmail.com",
        "--insert=INSERT_ROWS",
        "--no-input",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            log(f"OK → Registrado: {fecha} | {pasos} pasos")
            return True
        else:
            log(f"ERROR append: {result.stderr.strip()}")
            return False
    except Exception as e:
        log(f"ERROR en append: {e}")
        return False


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sincronizar pasos diarios HA → Sheets")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin escribir")
    parser.add_argument("--fecha", type=str, default=None, help="Forzar fecha (YYYY-MM-DD)")
    args = parser.parse_args()

    # 1. Obtener valor de pasos y fecha ART
    if args.fecha:
        # Modo fecha histórica: consulta el historial de HA para esa fecha
        fecha = args.fecha
        log(f"Modo histórico: consultando HA para {fecha}...")
        pasos = consultar_ha_historial(fecha)
        log(f"Valor histórico: {pasos} pasos para {fecha}")
    else:
        # Modo normal: consulta el estado actual del sensor
        log("Consultando Home Assistant...")
        pasos, last_updated_utc = consultar_ha()
        log(f"HA responde: {pasos} pasos | last_updated: {last_updated_utc}")
        fecha = utc_to_art_date(last_updated_utc)
        log(f"Fecha ART calculada: {fecha}")

    if not fecha:
        log("ERROR: no se pudo determinar la fecha")
        return 1

    if pasos < 0:
        log(f"ERROR: valor de pasos inválido: {pasos}")
        return 1

    # 3. Verificar duplicado (usa columna A)
    if fecha_ya_existe(fecha):
        log(f"SKIP → La fecha {fecha} ya está registrada")
        return 0

    # 4. Registrar
    if args.dry_run:
        log(f"DRY-RUN → Se registraría: {fecha} | {pasos}")
        return 0

    ok = append_a_planilla(fecha, pasos)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())