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

    # 1. Consultar HA
    log("Consultando Home Assistant...")
    try:
        pasos, last_updated_utc = consultar_ha()
        log(f"HA responde: {pasos} pasos | last_updated: {last_updated_utc}")
    except Exception as e:
        log(f"ERROR consultando HA: {e}")
        return 1

    # 2. Determinar fecha ART
    if args.fecha:
        fecha = args.fecha
        log(f"Fecha forzada (--fecha): {fecha}")
    else:
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