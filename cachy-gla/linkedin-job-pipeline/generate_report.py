#!/usr/bin/env python3
"""
Generador de informes de mercado semanal desde linkedin_jobs.db.

Uso:
    python generate_report.py                        # stdout (Markdown)
    python generate_report.py --output informe.md    # archivo Markdown
    python generate_report.py --html informe.html    # archivo HTML
"""

import argparse
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime

_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DIR, "linkedin_jobs.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def run_report():
    conn = get_conn()
    cur = conn.cursor()

    # Stats generales
    cur.execute("SELECT COUNT(*) FROM jobs")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT company) FROM jobs WHERE company != ''")
    empresas = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT location) FROM jobs WHERE location != ''")
    ubicaciones = cur.fetchone()[0]

    cur.execute("SELECT source, COUNT(*) as cnt FROM jobs GROUP BY source ORDER BY cnt DESC")
    fuentes = cur.fetchall()

    cur.execute("SELECT MIN(discovered_at), MAX(discovered_at) FROM jobs")
    min_date, max_date = cur.fetchone()
    min_date = min_date or "N/A"
    max_date = max_date or "N/A"

    # Roles
    cur.execute("SELECT title FROM jobs")
    titles = [row[0] for row in cur.fetchall()]

    def classify(title):
        t = title.lower()
        if any(x in t for x in ['data engineer', 'data engenh']): return 'Data Engineer'
        if any(x in t for x in ['platform engineer', 'platform']): return 'Platform'
        if any(x in t for x in ['data scien', 'data analytics', 'data analyst']): return 'Data Science/Analytics'
        if any(x in t for x in ['architect', 'arquitect']): return 'Architecture'
        if any(x in t for x in ['head', 'lead ', 'director', 'manager', 'jefe', 'gerente', 'chief', 'vp ', 'vice president']): return 'Leadership/Management'
        if any(x in t for x in ['engineer', 'ingenier']): return 'Other Engineering'
        return 'Other'

    roles = Counter(classify(t) for t in titles)

    def seniority(title):
        t = title.lower()
        if any(x in t for x in ['head', 'lead ', 'director', 'manager', 'chief', 'jefe', 'gerente', 'vp']): return 'Lead/Management'
        if any(x in t for x in ['senior', 'sr ', 'sr.', 'semi senior', 'ssr', 'semi-senior']): return 'Senior/Semi-Senior'
        if any(x in t for x in ['junior', 'jr ', 'jr.', 'trainee', 'entry']): return 'Junior'
        return 'Mid / Not specified'

    levels = Counter(seniority(t) for t in titles)

    # Top empresas
    cur.execute("SELECT company, COUNT(*) as cnt FROM jobs WHERE company != '' GROUP BY company ORDER BY cnt DESC LIMIT 15")
    top_companies = cur.fetchall()

    # Ubicaciones
    cur.execute("SELECT location, COUNT(*) as cnt FROM jobs WHERE location != '' GROUP BY location ORDER BY cnt DESC LIMIT 15")
    locations = cur.fetchall()

    # Tecnologías en títulos
    tech_keywords = {
        'Databricks': 'databricks', 'Snowflake': 'snowflake', 'AWS': 'aws',
        'Azure': 'azure', 'GCP': 'gcp', 'Python': 'python', 'SQL': 'sql',
        'Spark': 'spark', 'Kafka': 'kafka', 'Airflow': 'airflow',
        'Docker': 'docker', 'Kubernetes': 'kubernetes', 'Terraform': 'terraform',
        'MLOps': 'mlops', 'Machine Learning': 'machine learning',
    }
    tech_counts = {}
    for label, keyword in tech_keywords.items():
        c = sum(1 for t in titles if keyword in t.lower())
        if c > 0:
            tech_counts[label] = c

    # Remoto
    remote_keywords = ['remote', 'remoto', 'home', 'hibrido', 'híbrido', 'a distancia', '100%']
    remote_count = sum(1 for t in titles if any(k in t.lower() for k in remote_keywords))

    # Últimas ofertas
    cur.execute("SELECT title, company, location, source, job_url FROM jobs ORDER BY discovered_at DESC LIMIT 10")
    latest = cur.fetchall()

    conn.close()

    # --- Generar Markdown ---
    lines = []
    lines.append(f"# 📊 Informe de Mercado Data/Platform Engineering")
    lines.append(f"")
    lines.append(f"**Generado:** {datetime.now().strftime('%d/%m/%Y %H:%M')}hs")
    lines.append(f"**Período:** {min_date} → {max_date}")
    lines.append(f"")
    lines.append(f"## Resumen ejecutivo")
    lines.append(f"")
    lines.append(f"| Métrica | Valor |")
    lines.append(f"|---------|:-----:|")
    lines.append(f"| **Total ofertas** | {total} |")
    lines.append(f"| **Empresas distintas** | {empresas} |")
    lines.append(f"| **Ubicaciones distintas** | {ubicaciones} |")
    fuentes_str = ' + '.join(f'{r["source"]}={r["cnt"]}' for r in fuentes)
    lines.append(f"| **Fuentes** | {fuentes_str} |")
    lines.append(f"")
    lines.append(f"## Distribución por rol")
    lines.append(f"")
    lines.append(f"| Rol | Cantidad |")
    lines.append(f"|-----|:--------:|")
    for role, cnt in roles.most_common():
        bar = "▓" * min(cnt, 30)
        lines.append(f"| **{role}** | {cnt} {bar} |")
    lines.append(f"")
    lines.append(f"## Seniority")
    lines.append(f"")
    lines.append(f"| Nivel | Cantidad |")
    lines.append(f"|------|:--------:|")
    for level, cnt in levels.most_common():
        bar = "▓" * min(cnt, 30)
        lines.append(f"| **{level}** | {cnt} {bar} |")
    lines.append(f"")
    lines.append(f"## Top 15 empresas contratantes")
    lines.append(f"")
    lines.append(f"| Empresa | Ofertas |")
    lines.append(f"|--------|:--------:|")
    for row in top_companies:
        bar = "▓" * min(row['cnt'], 20)
        lines.append(f"| {row['company']} | {row['cnt']} {bar} |")
    lines.append(f"")
    lines.append(f"## Ubicaciones principales")
    lines.append(f"")
    lines.append(f"| Ubicación | Ofertas |")
    lines.append(f"|-----------|:--------:|")
    for row in locations:
        lines.append(f"| {row['location']} | {row['cnt']} |")
    lines.append(f"")
    if tech_counts:
        lines.append(f"## Tecnologías mencionadas en títulos")
        lines.append(f"")
        lines.append(f"| Tecnología | Menciones |")
        lines.append(f"|-----------|:---------:|")
        for tech, cnt in sorted(tech_counts.items(), key=lambda x: -x[1]):
            bar = "▓" * min(cnt, 20)
            lines.append(f"| {tech} | {cnt} {bar} |")
        lines.append(f"")
    lines.append(f"## Ofertas con mención remoto/híbrido: **{remote_count}**")
    lines.append(f"")
    lines.append(f"## Últimas 10 ofertas detectadas")
    lines.append(f"")
    for row in latest:
        lines.append(f"- **{row['title']}** @ {row['company']} ({row['location']}) · [{row['source']}]({row['job_url']})")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"*Generado por linkedin-job-pipeline · {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append(f"")

    # Scores section
    scores_block = add_top_scores_section(None)
    if scores_block:
        lines.append(scores_block)

    return "\n".join(lines)


def _fit_icon(fit: str) -> str:
    icons = {
        "excellent": "🟢",
        "good": "🔵",
        "fair": "🟡",
        "poor": "🔴",
    }
    return icons.get(fit, "⚪")


def add_top_scores_section(jobs_data):
    """Consulta job_scores y retorna bloque markdown con Top 10 ofertas mejor puntuadas."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT js.score, js.profile_fit, j.title, j.company, j.location, j.job_url "
        "FROM job_scores js "
        "JOIN jobs j ON js.job_url = j.job_url "
        "ORDER BY js.score DESC LIMIT 10"
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return ""

    lines = []
    lines.append(f"## 🏆 Top 10 Ofertas Mejor Puntuadas")
    lines.append(f"")
    lines.append(f"| # | Score | Fit | Título | Empresa | Ubicación |")
    lines.append(f"|---|-------|-----|--------|---------|-----------|")
    for i, row in enumerate(rows, 1):
        icon = _fit_icon(row["profile_fit"])
        title = (row["title"] or "-").replace("|", "\\|")
        company = (row["company"] or "-").replace("|", "\\|")
        location = (row["location"] or "-").replace("|", "\\|")
        score_str = f"{row['score']:.1f}" if row["score"] is not None else "-"
        lines.append(f"| {i} | {score_str} | {icon} {row['profile_fit']} | {title} | {company} | {location} |")
    lines.append(f"")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generar informe de mercado desde linkedin_jobs.db")
    parser.add_argument("--output", help="Archivo Markdown de salida (default: stdout)")
    parser.add_argument("--html", help="Archivo HTML de salida (convierte Markdown a HTML básico)")
    args = parser.parse_args()

    report = run_report()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"[report] Informe guardado en {args.output}", file=sys.stderr)
    elif args.html:
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Informe de Mercado Data/Platform Engineering</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; }}
h1 {{ color: #1a1a2e; border-bottom: 2px solid #e94560; padding-bottom: 10px; }}
h2 {{ color: #16213e; margin-top: 30px; }}
table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #1a1a2e; color: white; }}
tr:nth-child(even) {{ background: #f5f5f5; }}
a {{ color: #e94560; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
{report.replace('```', '<pre>').replace('```', '</pre>').replace('\n', '<br>\n')}
</body>
</html>"""
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[report] Informe HTML guardado en {args.html}", file=sys.stderr)
    else:
        print(report)

if __name__ == "__main__":
    main()