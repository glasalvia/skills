"""
Orquestador de consolidación.
Escanea triggers pendientes, parsea datos, sube a Drive y apende a Sheets.
"""
import os
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

# Agregar BASE_DIR al path
BASE_DIR = Path(os.path.expanduser("~/facturas"))
sys.path.insert(0, str(BASE_DIR))

from schema import FacturaData
from drive_manager import move_to_processed, move_to_failed, _load_env

GOG_BIN = "/home/linuxbrew/.linuxbrew/bin/gog"
FACTURAS_SHEET_ID = "1UPlbegaEvAV1UDCe6Poer1rerR8DpgYMl2jM2t8Hc6Q"


def get_pending_triggers() -> list[dict]:
    tmp_dir = BASE_DIR / "tmp"
    if not tmp_dir.exists():
        return []
    triggers = []
    for f in sorted(tmp_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            if data.get("status") == "pending":
                data["_trigger_file"] = str(f)
                triggers.append(data)
        except (json.JSONDecodeError, KeyError):
            continue
    return triggers


def mark_trigger_done(trigger: dict, success: bool = True):
    trigger_file = Path(trigger.get("_trigger_file", ""))
    if not trigger_file.exists():
        return
    trigger["status"] = "done" if success else "failed"
    trigger["processed_at"] = datetime.now().isoformat()
    with open(trigger_file, "w") as f:
        json.dump(trigger, f, indent=2, ensure_ascii=False)


def append_to_sheets(data: FacturaData, sheet_id: str = None) -> bool:
    if sheet_id is None:
        sheet_id = FACTURAS_SHEET_ID
    row = [[
        data.fecha_factura.isoformat(),
        data.cuit,
        data.comercio,
        data.conceptos,
        str(data.monto_total),
        str(data.impuestos) if data.impuestos is not None else "",
        data.drive_link,
        data.fecha_procesamiento.isoformat(),
        str(data.score_confianza),
    ]]
    values_json = json.dumps(row)
    env = os.environ.copy()
    cmd = [
        GOG_BIN, "--account", "raspilasalvia@gmail.com", "--no-input",
        "sheets", "append", sheet_id,
        "Facturas!A:I",
        "--values-json", values_json,
        "--insert", "INSERT_ROWS",
        "-y",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
    if result.returncode != 0:
        print(f"Error GOG sheets: {result.stderr}", file=sys.stderr)
        return False
    return True


def process_trigger(trigger: dict, parsed_data: dict) -> bool:
    trigger_id = trigger.get("id", "unknown")
    clean_path = trigger.get("clean_path", "")
    original_path = str(BASE_DIR / "tmp" / trigger.get("original_name", ""))
    try:
        factura = FacturaData(**parsed_data)
        if factura.score_confianza < 0.80:
            print(f"[{trigger_id}] Score bajo ({factura.score_confianza}), moviendo a failed")
            move_to_failed(clean_path, f"score_confianza={factura.score_confianza}")
            mark_trigger_done(trigger, success=False)
            return False
        drive_result = move_to_processed(original_path, clean_path)
        factura.drive_link = drive_result["drive_link"]
        factura.fecha_procesamiento = datetime.now()
        ok = append_to_sheets(factura)
        if not ok:
            print(f"[{trigger_id}] Error al escribir en Sheets", file=sys.stderr)
            mark_trigger_done(trigger, success=False)
            return False
        for p in [clean_path, original_path]:
            if p and os.path.exists(p):
                os.remove(p)
        print(f"[{trigger_id}] Procesado OK | {factura.comercio} | ${factura.monto_total}")
        mark_trigger_done(trigger, success=True)
        return True
    except Exception as e:
        print(f"[{trigger_id}] Error: {e}")
        if clean_path and os.path.exists(clean_path):
            move_to_failed(clean_path, str(e))
        mark_trigger_done(trigger, success=False)
        return False


if __name__ == "__main__":
    triggers = get_pending_triggers()
    if not triggers:
        print("No hay triggers pendientes.")
        sys.exit(0)
    print(f"{len(triggers)} trigger(s) pendiente(s):")
    for t in triggers:
        print(f"   - {t['id']} | {t.get('original_name', '?')}")
    print("Ejecuta la Skill para procesar con LLM y consolidar.")
