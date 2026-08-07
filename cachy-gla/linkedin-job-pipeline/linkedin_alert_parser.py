#!/usr/bin/env python3
"""Parser de alertas de empleo de LinkedIn por email (vía gog CLI).

Busca emails de jobalerts-noreply@linkedin.com, parsea los jobs del cuerpo
y los devuelve en formato JSON.

Uso:
    python linkedin_alert_parser.py [--dry-run] [--output FILE]
"""

import argparse
import json
import re
import subprocess
import sys
from typing import Optional


def run_gog(args: list[str]) -> tuple[int, str, str]:
    """Ejecutar un comando gog y devolver (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["gog"] + args,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def search_emails(max_results: int = 20) -> list[str]:
    """Buscar emails de LinkedIn y devolver lista de IDs."""
    rc, stdout, stderr = run_gog([
        "gmail", "search",
        "from:jobalerts-noreply@linkedin.com newer_than:7d",
        f"--max", str(max_results),
        "--no-input",
    ])
    if rc != 0:
        print(f"[WARN] gog gmail search falló (rc={rc}): {stderr.strip()}", file=sys.stderr)
        return []

    lines = [l.strip() for l in stdout.strip().splitlines() if l.strip()]
    # La salida de gog search es tabular con encabezado.
    # Saltar la fila de encabezado (empieza con 'ID').
    ids: list[str] = []
    for line in lines:
        parts = line.split()
        if not parts or parts[0].upper() == "ID":
            continue
        # Solo incluir líneas que parezcan datos reales (IDs hexadecimales largos).
        if re.match(r'^[0-9a-f]+$', parts[0], re.IGNORECASE) and len(parts[0]) >= 16:
            ids.append(parts[0])
    return ids


def read_email(email_id: str) -> tuple[dict[str, str], str]:
    """Leer un email y devolver (headers_dict, body_text)."""
    rc, stdout, stderr = run_gog([
        "gmail", "read", email_id, "--no-input",
    ])
    if rc != 0:
        print(f"[WARN] gog gmail read falló para {email_id} (rc={rc}): {stderr.strip()}", file=sys.stderr)
        return {}, ""

    text = stdout
    # gog gmail read envuelve el contenido con metadata:
    #   "read contains X message(s)"
    #   "=== Message N/M: <ID> ==="
    #   "From:", "To:", etc.
    # Separar headers del body por línea vacía.
    header_lines: list[str] = []
    body_start = 0
    for i, line in enumerate(text.splitlines()):
        if line == "":
            body_start = i + 1
            break
        header_lines.append(line)

    headers = {}
    for hl in header_lines:
        if ":" in hl:
            key, _, val = hl.partition(":")
            headers[key.strip()] = val.strip()

    # Strip wrapper lines del body (metadata de gog).
    raw_body = text[body_start:].strip() if body_start < len(text.splitlines()) else ""
    cleaned_lines: list[str] = []
    for line in raw_body.splitlines():
        stripped = line.strip()
        # Saltar líneas wrapper de gog.
        if re.match(r'^read contains \d+ message\(s\)', stripped, re.IGNORECASE):
            continue
        if re.match(r'^===\s*Message', stripped):
            continue
        cleaned_lines.append(line)
    body = "\n".join(cleaned_lines).strip()
    return headers, body


def parse_jobs_from_body(body: str) -> list[dict]:
    """Parsear jobs del cuerpo de texto del email.

    Los jobs están separados por líneas de guiones '---'.
    Cada job tiene: title, company, location, badge (opcional), job_url, job_id.
    """
    jobs = []
    # Separar por líneas de guiones.
    blocks = re.split(r"^-{20,}$", body, flags=re.MULTILINE)

    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if not lines:
            continue

        # Filtrar líneas que son partes del encabezado del email (no jobs).
        filtered_lines: list[str] = []
        for l in lines:
            # Saltar líneas de metadata del email.
            if re.match(r'^===\s+Message', l):
                continue
            if l.startswith('From:') or l.startswith('To:') or l.startswith('Subject:') or l.startswith('Date:'):
                continue
            if l.lower().startswith('tu alerta de empleo'):
                continue
            if l.lower().startswith('ver todos los empleos'):
                break  # footer
            filtered_lines.append(l)
        lines = filtered_lines

        if not lines:
            continue

        # Verificar que este bloque parece un job (tiene "Ver anuncio de empleo:" o URL en alguna línea).
        has_job_url = any("Ver anuncio de empleo:" in l for l in lines)
        if not has_job_url and not re.search(r"https://www\.linkedin\.com/comm/jobs/", "\n".join(lines)):
            # Podría ser el encabezado o footer — saltar.
            continue

        job: dict = {}

        # Extraer job_id de la URL si está disponible.
        full_text = block.strip()
        url_match = re.search(r"https://www\.linkedin\.com/comm/jobs/view/(\d+)/", full_text)
        if url_match:
            job["job_id"] = url_match.group(1)

        # Extraer job_url.
        for l in lines:
            if "Ver anuncio de empleo:" in l:
                job["job_url"] = l.replace("Ver anuncio de empleo:", "").strip()
                break

        # Si no se encontró URL en el formato esperado, buscar cualquier URL de LinkedIn jobs.
        if "job_url" not in job:
            url_match2 = re.search(r"(https://www\.linkedin\.com/comm/jobs/view/\d+/)", full_text)
            if url_match2:
                job["job_url"] = url_match2.group(1)

        # Determinar si hay badge (cuarta línea, antes del link).
        # Regex para detectar badges conocidos.
        known_badges = [
            r"Solicitar con perfil y CV",
            r"Candidato destacado",
            r"Esta empresa busca personal activamente",
            r"Crecimiento rápido",
            r"Solicitud fácil",
            r"Nueva",
        ]
        badge_pattern = re.compile("|".join(known_badges))

        # Construir job desde las líneas.
        # title = primera línea, company = segunda, location = tercera.
        # badge = cuarta si coincide con patrón de badge.
        if len(lines) >= 1:
            job["title"] = lines[0]
        if len(lines) >= 2:
            job["company"] = lines[1]
        if len(lines) >= 3:
            job["location"] = lines[2]

        # Verificar si la cuarta línea es un badge (y no la URL del anuncio).
        if len(lines) >= 4 and "Ver anuncio de empleo:" not in lines[3]:
            if badge_pattern.search(lines[3]):
                job["badge"] = lines[3]

        if job.get("job_id"):
            jobs.append(job)

    return jobs


def deduplicate(jobs: list[dict]) -> list[dict]:
    """Deduplicar jobs por job_id, manteniendo el primer orden."""
    seen_ids: set[str] = set()
    unique: list[dict] = []
    for job in jobs:
        jid = job.get("job_id", "")
        if jid and jid not in seen_ids:
            seen_ids.add(jid)
            unique.append(job)
    return unique


def extract_seniority(title: str, description: str) -> str:
    """Detectar senioridad del puesto a partir de título y descripción.

    Retorna: 'lead', 'senior', 'mid', 'junior' o 'mid' (fallback).
    """
    text = f"{title} {description}".lower()

    # lead-level keywords
    if re.search(r'\b(lead|head of|director|manager|sr manager|principal)\b', text):
        return "lead"

    # senior-level keywords
    if re.search(r'\bsenior\b|\bsr\s|\bstaff\b', text):
        return "senior"

    # junior-level keywords
    if re.search(r'\bjunior\b|\bjr\s|\bentry\b|\btrainee\b', text):
        return "junior"

    # mid-level keywords
    if re.search(r'\bmid\b|\bintermediate\b|\bmid[- ]?level\b', text):
        return "mid"

    # default fallback
    return "mid"


def is_remote(location: str, description: str) -> bool:
    """Detectar si el puesto es remote (100% remoto).

    Retorna True si 'remote' aparece en location o descripción.
    False para 'hybrid' o cualquier otro caso.
    """
    loc = location.lower()
    desc = description.lower()

    if re.search(r'\bhybrid\b', loc) or re.search(r'\bhybrid\b', desc):
        return False

    if re.search(r'\bremote\b', loc) or re.search(r'\bremote\b', desc):
        return True

    return False


def extract_salary(description: str) -> tuple:
    """Buscar rangos salariales en la descripción.

    Retorna (salary_min, salary_max, currency) o (None, None, None).
    Detecta patrones como '$100k - $150k', 'USD 100K', etc.
    """
    if not description:
        return (None, None, None)

    desc = description.strip()

    # Detectar moneda primero (buscar símbolos o códigos de divisa).
    currency = None
    for curr in ["USD", "EUR", "GBP", "BRL", "ARS", "COP", "MXN", "CLP", "PEN"]:
        if re.search(r'\b' + curr + r'\b', desc, re.IGNORECASE):
            currency = curr
            break
    # Símbolos de moneda.
    symbol_map = {"$": "USD", "€": "EUR", "£": "GBP"}
    for sym, curr in symbol_map.items():
        if sym in desc and not currency:
            currency = curr
            break

    # Buscar patrones de rango salarial.
    # Patrón 1: $100k - $150k o $100,000 - $150,000
    pattern_range = re.compile(
        r'(?:\$|€|£)?\s*(\d{1,3}(?:[,\s]?\d{3})*)'
        r'\s*[-–—]\s*'
        r'(?:\$|€|£)?\s*(\d{1,3}(?:[,\s]?\d{3})*)',
        re.IGNORECASE
    )
    # Patrón 2: USD 100K - 150K o similar (con currency code)
    pattern_range2 = re.compile(
        r'(USD|EUR|GBP|BRL|ARS|COP|MXN|CLP|PEN)\s+(\d{1,3}(?:[,\s]?\d{3})*)'
        r'\s*[-–—]\s*'
        r'(\d{1,3}(?:[,\s]?\d{3})*)',
        re.IGNORECASE
    )

    # Patrón 3: $100K-$150K (sin espacio en el separador)
    pattern_range3 = re.compile(
        r'(\$|€|£)(\d+)(?:,\d{3})*(?:[kK])?\s*-\s*(\$|€|£)?(\d+)(?:,\d{3})*(?:[kK])?',
    )

    min_val = None
    max_val = None

    # Intentar patrón con código de moneda primero.
    m2 = pattern_range2.search(desc)
    if m2:
        currency = m2.group(1).upper()
        min_val = _parse_number(m2.group(2))
        max_val = _parse_number(m2.group(3))
        return (min_val, max_val, currency)

    # Intentar patrón con símbolo.
    m3 = pattern_range3.search(desc)
    if m3:
        sym1 = m3.group(1)
        min_raw = m3.group(2)
        max_raw = m3.group(4)
        if currency is None and sym1 == "$":
            currency = "USD"
        elif currency is None and sym1 == "€":
            currency = "EUR"
        elif currency is None and sym1 == "£":
            currency = "GBP"
        min_val = _parse_number(min_raw)
        max_val = _parse_number(max_raw)
        return (min_val, max_val, currency)

    # Intentar patrón genérico sin símbolo.
    m = pattern_range.search(desc)
    if m:
        min_val = _parse_number(m.group(1))
        max_val = _parse_number(m.group(2))
        return (min_val, max_val, currency)

    return (None, None, None)


def _parse_number(raw: str) -> Optional[float]:
    """Convertir string numérico con K/M/símbolos a float."""
    if not raw:
        return None
    cleaned = raw.replace(",", "").replace(" ", "")
    mult = 1
    upper = cleaned.upper()
    if upper.endswith("K"):
        mult = 1_000
        cleaned = cleaned[:-1]
    elif upper.endswith("M"):
        mult = 1_000_000
        cleaned = cleaned[:-1]
    try:
        return float(cleaned) * mult
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser(description="Parsear alertas de empleo de LinkedIn por email.")
    parser.add_argument("--dry-run", action="store_true", help="Solo imprimir jobs en JSON por stdout.")
    parser.add_argument("--output", type=str, default=None, help="Archivo de salida JSON.")
    parser.add_argument("--to-db", action="store_true", help="Insertar jobs en linkedin_jobs.db.")
    args = parser.parse_args()

    # 1. Buscar emails.
    email_ids = search_emails(max_results=20)
    if not email_ids:
        print(json.dumps([], indent=2))
        sys.exit(0)

    all_jobs: list[dict] = []

    # 2. Leer cada email y parsear jobs.
    for eid in email_ids:
        headers, body = read_email(eid)

        if not body:
            continue

        # Extraer fecha y subject del header.
        email_date = headers.get("Date", "")
        email_subject = headers.get("Subject", "")

        jobs = parse_jobs_from_body(body)

        for job in jobs:
            job["email_date"] = email_date
            job["email_subject"] = email_subject

            # --- Campos extraídos (seniority, remote, salary) ---
            job["seniority"] = extract_seniority(
                job.get("title", ""), job.get("description", "")
            )
            job["remote"] = is_remote(
                job.get("location", ""), job.get("description", "")
            )
            salary_min, salary_max, salary_currency = extract_salary(
                job.get("description", "")
            )
            job["salary_min"] = salary_min
            job["salary_max"] = salary_max
            job["salary_currency"] = salary_currency

        all_jobs.extend(jobs)

    # 3. Deduplicar por job_id.
    unique_jobs = deduplicate(all_jobs)

    # 4. Output.
    output_json = json.dumps(unique_jobs, indent=2, ensure_ascii=False)

    if args.to_db:
        from db_setup import init_db, insert_job_with_extras

        conn = init_db()
        inserted = 0
        for job in unique_jobs:
            # source fijo para emails de LinkedIn
            job["source"] = "linkedin_email"
            if insert_job_with_extras(conn, job):
                inserted += 1
        conn.close()
        print(f"[parser] {inserted} jobs insertados en linkedin_jobs.db", file=sys.stderr)
    elif args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json + "\n")
        print(f"[OK] {len(unique_jobs)} jobs escritos en {args.output}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
