#!/usr/bin/env python3
"""
Capa 2 — Scraping multi-board de empleos con python-jobspy.

Busca ofertas en LinkedIn, Indeed y Google Jobs, imprime resultados como JSON por stdout
o los guarda en un archivo con --output.
"""

import argparse
import json
import math
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Enriquecimiento de jobs: seniority, remote, salary
# ---------------------------------------------------------------------------

def extract_seniority(title: str, description: str) -> str:
    """Determina el nivel seniority del puesto."""
    text = f"{title} {description}".lower()
    if any(k in text for k in ["lead", "head", "director", "manager", "sr manager", "principal"]):
        return "lead"
    if any(k in text for k in ["senior", "sr ", "staff"]):
        return "senior"
    if any(k in text for k in ["mid", "intermediate"]):
        return "mid"
    if any(k in text for k in ["junior", "jr ", "entry", "trainee"]):
        return "junior"
    return "mid"


def is_remote(location: str, description: str) -> bool:
    """Determina si el puesto es remoto."""
    loc = location.lower()
    desc = description.lower()
    if "remote" in loc or "remote" in desc:
        return True
    if "hybrid" in loc or "hybrid" in desc:
        return False
    return False


def extract_salary(description: str) -> tuple:
    """Extrae salario min, max y moneda de la descripción.

    Retorna (salary_min, salary_max, currency).
    Si no se encuentra nada retorna (None, None, None).
    """
    if not description:
        return None, None, None

    desc = description
    # Monedas reconocidas (orden largo primero para evitar falsos positivos)
    currencies = ["ARS", "MXN", "COP", "CLP", "BRL", "PEN", "EUR", "GBP", "USD"]

    # Patrón: $100k-$150k  o  $100,000-$150,000  o  USD 100K-150K
    # Buscamos primero con moneda explícita
    for cur in currencies:
        pattern = rf"{cur}\s*([\d,.]+)\s*-?\s*[&]?\s*([\d,.]+)(?:\s*(?:K|M)|\b)"
        m = re.search(pattern, desc, re.IGNORECASE)
        if m:
            lo_str, hi_str = m.group(1), m.group(2)
            low = _parse_amount(lo_str)
            high = _parse_amount(hi_str)
            return (low, high, cur)

    # Sin moneda explícita: $ o £ símbolo
    pattern = r"[$£]\s*([\d,.]+)\s*-?\s*[&]?\s*([$£\d,.]+)(?:\s*(?:K|M)|\b)"
    m = re.search(pattern, desc)
    if m:
        lo_str = m.group(1).replace(',', '')
        hi_str = m.group(2).lstrip('$£').replace(',', '')
        low = _parse_amount(lo_str)
        high = _parse_amount(hi_str)
        return (low, high, "USD")  # default

    return None, None, None


def _parse_amount(s: str) -> float:
    """Convierte '100K', '150000', etc. a número."""
    s = s.strip().upper()
    multiplier = 1
    if s.endswith('M'):
        multiplier = 1_000_000
        s = s[:-1]
    elif s.endswith('K'):
        multiplier = 1_000
        s = s[:-1]
    return float(s.replace(',', '')) * multiplier


def ensure_jobspy():
    """Verifica que python-jobspy esté instalado; si no, lo instala."""
    try:
        import jobspy  # noqa: F401
    except ImportError:
        print("[jobspy] Instalando python-jobspy ...", file=sys.stderr)
        # Arch Linux / PEP 668 requiere --break-system-packages
        pip_flags = [sys.executable, "-m", "pip", "install", "python-jobspy", "--quiet"]
        result = subprocess.run(
            pip_flags + ["--break-system-packages"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"[jobspy] ERROR al instalar: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        print("[jobspy] Instalado correctamente.", file=sys.stderr)


def scrape_jobs(args):
    import jobspy

    boards = ["linkedin", "indeed", "google"]
    all_jobs = []
    failed_boards = []

    for board in boards:
        try:
            df = jobspy.scrape_jobs(
                site_name=[board],
                search_term=args.search,
                location=args.location,
                results_wanted=args.max,
                hours_old=args.hours,
            )
            if hasattr(df, 'empty') and not df.empty:
                all_jobs.extend(df.to_dict(orient='records'))
            print(f"[jobspy] {board}: {len(all_jobs)} resultados", file=sys.stderr)
        except Exception as e:
            failed_boards.append(board)
            print(f"[jobspy] WARNING: {board} falló — {e}", file=sys.stderr)

    if not all_jobs and failed_boards:
        print(
            f"[jobspy] ERROR: Todos los boards fallaron ({', '.join(failed_boards)}).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Deduplicar por URL
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        url = job.get('job_url', '') or ''
        if url and url not in seen:
            seen.add(url)
            unique_jobs.append(job)

    # Normalizar a lista de dicts compatibles con la DB SQLite unificada
    results = []
    for job in unique_jobs:
        date_val = job.get('date_posted')
        # Manejar NaN / None de pandas
        is_nan = False
        if isinstance(date_val, float):
            try:
                is_nan = math.isnan(date_val)
            except (ValueError, TypeError):
                pass
        if date_val is None or is_nan:
            date_str = ""
        elif hasattr(date_val, 'isoformat'):
            date_str = date_val.isoformat()
        else:
            date_str = str(date_val)

        description_text = (job.get('description', '') or '').strip() or ''

        # Enriquecer con campos adicionales
        job_seniority = extract_seniority(job.get('title', ''), description_text)
        job_remote = is_remote(job.get('location', ''), description_text)
        salary_min, salary_max, salary_currency = extract_salary(description_text)

        enriched = {
            "title": job.get('title', '') or '',
            "company": job.get('company', '') or '',
            "location": job.get('location', '') or '',
            "source": job.get('site', ''),
            "job_url": job.get('job_url', '') or '',
            "date_posted": date_str,
            "description": description_text,
            # Campos enriquecidos
            "seniority": job_seniority,
            "remote": job_remote,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
        }
        results.append(enriched)

    output = json.dumps(results, ensure_ascii=False, indent=2)

    if args.dry_run:
        # Enrich output for dry-run display
        enriched_output = []
        for job in results:
            enriched_output.append({
                **job,
                "salary_range": f"{job['salary_currency']} {job['salary_min']} - {job['salary_max']}" if job['salary_min'] and job['salary_max'] else None,
            })
        output = json.dumps(enriched_output, ensure_ascii=False, indent=2)

    if args.to_db:
        from db_setup import init_db, insert_job_with_extras

        conn = init_db()
        inserted = 0
        for job in results:
            if insert_job_with_extras(conn, job):
                inserted += 1
        conn.close()
        print(f"[jobspy] {inserted} jobs insertados en linkedin_jobs.db", file=sys.stderr)
    elif args.output:
        # Enrich output for dry-run display
        if args.dry_run:
            enriched_output = []
            for job in results:
                enriched_output.append({
                    **job,
                    "salary_range": f"{job['salary_currency']} {job['salary_min']} - {job['salary_max']}" if job['salary_min'] and job['salary_max'] else None,
                })
            output = json.dumps(enriched_output, ensure_ascii=False, indent=2)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"[jobspy] {len(results)} jobs guardados en {args.output}", file=sys.stderr)
    else:
        print(output)


def main():
    parser = argparse.ArgumentParser(
        description="Scraping multi-board de empleos con python-jobspy"
    )
    parser.add_argument("--search", default="data engineer", help="Término de búsqueda (default: data engineer)")
    parser.add_argument("--location", default="Argentina", help="Ubicación (default: Argentina)")
    parser.add_argument("--max", type=int, default=25, help="Resultados máximos (default: 25)")
    parser.add_argument("--hours", type=int, default=72, help="Horas hacia atrás (default: 72)")
    parser.add_argument("--output", help="Archivo JSON de salida (default: stdout)")
    parser.add_argument("--to-db", action="store_true", help="Insertar jobs en linkedin_jobs.db.")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar resultados enriquecidos sin escribir DB ni archivo.")
    args = parser.parse_args()

    ensure_jobspy()
    if args.dry_run:
        import json as _json
        results = scrape_jobs(args)
        enriched = []
        for job in results:
            enriched.append({
                **job,
                "seniority": job.get("seniority", "mid"),
                "remote": job.get("remote", False),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "salary_currency": job.get("salary_currency"),
            })
        print(_json.dumps(enriched, ensure_ascii=False, indent=2))
        return
    scrape_jobs(args)


if __name__ == "__main__":
    main()
