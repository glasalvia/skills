#!/usr/bin/env python3
"""Exporta ofertas top con scoring >= 70 para integración WhatsApp."""

import argparse
import sys
from pathlib import Path

PARENT = Path(__file__).resolve().parent
DB_PATH = PARENT / "linkedin_jobs.db"

sys.path.insert(0, str(PARENT))
from db_setup import get_connection


def export_digest(top_n=5, min_score=70, hours=24):
    """Consulta DB y devuelve texto plano con top ofertas."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT j.title, j.company, j.location, j.job_url,
               js.score, js.profile_fit
        FROM job_scores js
        JOIN jobs j ON js.job_url = j.job_url
        WHERE js.score >= ?
          AND j.discovered_at >= datetime('now', ?)
        ORDER BY js.score DESC
        LIMIT ?
    """, (min_score, f'-{hours} hours', top_n)).fetchall()
    conn.close()

    if not rows:
        return "🔍 No hay nuevas ofertas destacadas en las últimas 24h."

    lines = ["🔍 *Ofertas LinkedIn destacadas*\n"]
    for i, r in enumerate(rows, 1):
        icon = {"excellent": "🟢", "good": "🔵", "fair": "🟡", "poor": "🔴"}
        lines.append(
            f"{i}. {icon.get(r['profile_fit'], '⚪')} *{r['title']}*\n"
            f"   {r['company']} — {r['location']}\n"
            f"   Score: {r['score']}/100 | {r['profile_fit'].upper()}\n"
            f"   {r['job_url']}\n"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Exporta digest LinkedIn para WhatsApp")
    parser.add_argument("--top", type=int, default=5, help="Top N ofertas (defecto 5)")
    parser.add_argument("--min-score", type=int, default=70, help="Score mínimo (defecto 70)")
    parser.add_argument("--hours", type=int, default=24, help="Ventana en horas (defecto 24)")
    args = parser.parse_args()

    print(export_digest(top_n=args.top, min_score=args.min_score, hours=args.hours))


if __name__ == "__main__":
    main()