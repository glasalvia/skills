#!/usr/bin/env python3
"""
daily_digest.py — Digest diario de ofertas con scoring y envío Telegram.

Orquesta linkedin_alert_parser.py y profile_matcher.py, consulta la DB
linkedin_jobs.db y formatea un mensaje de texto plano compatible con Telegram
para las top N ofertas con score >= 60.

Uso:
    python3 daily_digest.py                  # full run + mensaje
    python3 daily_digest.py --dry-run        # solo imprime digest en stdout
    python3 daily_digest.py --top 10         # top N ofertas (default 5)
    python3 daily_digest.py --skip-fetch     # no ejecutar alert parser ni matcher

TODO: El envío de la notificación por Telegram se integrará luego vía sessions_send o message tool.
"""

import argparse
import os
import sqlite3
import subprocess
import sys
from datetime import date

# ── Paths ────────────────────────────────────────────────────────────────
WORKSPACE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(WORKSPACE, "linkedin_jobs.db")
PARSER_SCRIPT = os.path.join(WORKSPACE, "linkedin_alert_parser.py")
MATCHER_SCRIPT = os.path.join(WORKSPACE, "profile_matcher.py")

# ── Constants ────────────────────────────────────────────────────────────
TITLE = "Data Platform"
DIGEST_HEADER = f"🔍 *{TITLE} - Digest Diario*"
MIN_SCORE = 60


def run_script(name: str, args: list[str]) -> tuple[str, str]:
    """Execute a Python script and return (stdout, stderr)."""
    try:
        result = subprocess.run(
            ["python3", name] + args,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return "", f"{name} not found"
    except subprocess.TimeoutExpired:
        return "", f"{name} timed out after 120s"


def fetch_jobs(top_n: int) -> list[dict]:
    """Query the DB for top N jobs with score >= MIN_SCORE."""
    if not os.path.exists(DB_PATH):
        return []

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT j.title, j.company, j.location, j.job_url, "
            "js.score, js.profile_fit "
            "FROM job_scores js JOIN jobs j ON js.job_url = j.job_url "
            "WHERE js.score >= ? "
            "ORDER BY js.score DESC LIMIT ?",
            (MIN_SCORE, top_n),
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except sqlite3.Error:
        return []


def score_label(score: float) -> str:
    """Return a color label for the score."""
    if score >= 80:
        return "🟢 excellent"
    elif score >= 70:
        return "🔵 good"
    else:
        return "🟡 fair"


def format_digest(jobs: list[dict], top_n: int) -> str:
    """Format the digest message as plain text compatible with Telegram."""
    lines = [DIGEST_HEADER, f"📅 {date.today().isoformat()}", ""]

    if not jobs:
        lines.append("No se encontraron ofertas destacadas hoy.")
        return "\n".join(lines)

    lines.append(f"🏆 *Top {top_n} Ofertas*\n")

    for i, job in enumerate(jobs, 1):
        label = score_label(job["score"])
        lines.append(
            f"{i}. *{job['title']}* @ {job['company']}\n"
            f"   Score: {job['score']:.1f} {label}\n"
            f"   📍 {job['location']}\n"
            f"   🔗 {job['job_url']}\n"
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Daily digest of Data Platform jobs.")
    parser.add_argument("--dry-run", action="store_true", help="Skip fetching, only format and print digest")
    parser.add_argument("--top", type=int, default=5, help="Number of top offers to show (default: 5)")
    parser.add_argument("--skip-fetch", action="store_true", help="Skip running alert parser and matcher")
    args = parser.parse_args()

    # ── Step 1: Orchestrate fetchers ───────────────────────────────────
    if not args.skip_fetch and not args.dry_run:
        print("→ Ejecutando linkedin_alert_parser.py ...", file=sys.stderr)
        out, err = run_script(PARSER_SCRIPT, ["--to-db"])
        if out:
            print(f"  [parser] {out}", file=sys.stderr)
        if err:
            print(f"  [parser ERR] {err}", file=sys.stderr)

        print("→ Ejecutando profile_matcher.py ...", file=sys.stderr)
        out, err = run_script(MATCHER_SCRIPT, ["--to-db"])
        if out:
            print(f"  [matcher] {out}", file=sys.stderr)
        if err:
            print(f"  [matcher ERR] {err}", file=sys.stderr)

    # ── Step 2: Query DB ───────────────────────────────────────────────
    jobs = fetch_jobs(args.top)

    # ── Step 3: Format message ─────────────────────────────────────────
    message = format_digest(jobs, args.top)

    # ── Step 4: Output ─────────────────────────────────────────────────
    print(message)

    # TODO: Integrar envío de notificación por Telegram vía sessions_send
    # o message tool. Aquí iría la llamada a la herramienta correspondiente.


if __name__ == "__main__":
    main()
