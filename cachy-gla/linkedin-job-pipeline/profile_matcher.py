#!/usr/bin/env python3
"""Motor de scoring de ofertas contra perfil del candidato."""

import sqlite3
import yaml
import re
import sys
import json
import argparse
from pathlib import Path

PARENT = Path(__file__).resolve().parent
DB_PATH = PARENT / "linkedin_jobs.db"
PROFILE_PATH = PARENT / "profile.yaml"


def load_profile():
    """Carga perfil desde profile.yaml."""
    if not PROFILE_PATH.exists():
        print("[profile_matcher] ERROR: No existe profile.yaml en workspace", file=sys.stderr)
        sys.exit(1)
    with open(PROFILE_PATH, "r") as f:
        profile = yaml.safe_load(f)
    return profile["candidate"]


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn):
    """Asegura que job_scores existe."""
    from db_setup import upgrade_schema
    upgrade_schema(conn)


def title_match(title, profile):
    """Score de cobertura de título laboral (25% del total). [0-100]"""
    t = title.lower().strip()
    score = 10  # base

    core_patterns = profile.get("current_title", "").lower()
    keywords = profile.get("skills", {}).get("core", [])

    # Exact match patterns
    if re.search(r"\bdata\s*platform\b", t):
        score = 100
    elif re.search(r"\bdata\s*engineer\b", t) and "platform" in t:
        score = 95
    elif re.search(r"\bdata\s*engineer\b", t):
        score = 85
    elif re.search(r"\bplatform\s*engineer\b", t):
        score = 85
    elif re.search(r"\bdata\s*architect\b", t):
        score = 85
    elif re.search(r"\bbig\s*data\b", t):
        score = 85
    elif re.search(r"\bcloud\s*architect\b", t):
        score = 85
    elif re.search(r"\bdata\b", t) and re.search(r"\bengineer\b", t):
        score = 70
    elif re.search(r"\bdata\b", t) or re.search(r"\bengineer\b", t) or re.search(r"\bplatform\b", t):
        score = 50

    # Bonus for seniority fitting Data Platform Sr Manager
    if score >= 70 and re.search(r"\b(manager|lead|head|director|principal|sr\.?\s*manager|senior\s*manager)\b", t):
        score = min(score + 15, 100)

    return score


def seniority_match(title, description, profile):
    """Score de correspondencia de jerarquía laboral (20% del total). [0-100]"""
    text = (title + " " + (description or "")).lower()

    if re.search(r"\b(lead|head|director|principal|architect)\b", text):
        return 100
    if re.search(r"\b(manager|sr\s*manager|senior\s*manager)\b", text):
        return 100
    if re.search(r"\b(senior|sr[.\s]|staff)\b", text):
        return 70
    if re.search(r"\b(mid|intermediate|ssr)\b", text):
        return 30
    if re.search(r"\b(junior|jr[.\s]|entry|trainee)\b", text):
        return 0
    return 50


def skills_match(title, description, profile):
    """Score de cobertura de skills (25% del total). [0-100]"""
    text = (title + " " + (description or "")).lower()
    core = profile.get("skills", {}).get("core", [])
    secondary = profile.get("skills", {}).get("secondary", [])

    if not core and not secondary:
        return 50

    # Core skills weighted 70% of skills component
    core_matches = 0
    for skill in core:
        if skill.lower() in text:
            core_matches += 1
    core_frac = core_matches / len(core) if core else 0

    # Secondary skills weighted 30%
    sec_matches = 0
    for skill in secondary:
        if skill.lower() in text:
            sec_matches += 1
    sec_frac = sec_matches / len(secondary) if secondary else 1.0

    combined = min(core_frac * 0.70 + sec_frac * 0.30, 1.0)
    return round(combined * 100, 1)


def location_match(location, profile):
    """Score de ubicación (10% del total). [0-100]"""
    loc = (location or "").lower()

    if not loc.strip():
        return 50

    has_remote = "remote" in loc
    if has_remote:
        if "argentina" in loc:
            return 100
        if "latam" in loc or "latin america" in loc:
            return 80
        if "us" in loc or "united states" in loc:
            return 60
        if "brazil" in loc or "brasil" in loc:
            return 40
        return 70

    if "buenos aires" in loc:
        return 50

    return 30


def company_relevance(company, profile):
    """Score de empresa (15% del total). [0-100]"""
    c = (company or "").lower()

    if not c.strip():
        return 50

    # Big tech
    if re.search(r"\b(meta|google|amazon|apple|netflix|microsoft|openai)\b", c):
        return 100

    # Data-first
    if re.search(r"\b(databricks|snowflake|confluent|datadog|palantir|elastic|mongodb|splunk)\b", c):
        return 90

    # Known good companies (from existing data)
    if re.search(r"\b(blend|ninjaone|lumenalta|capgemini)\b", c):
        return 80

    # Tech-related keywords
    if re.search(r"\b(tech|data|cloud|ai|digital|software|labs|inc\.?|llc\.?)\b", c):
        return 70

    # Finance/Fintech
    if re.search(r"\b(bank|banco|financial|fintech|pay|bbva|santander|galicia|macro|hipotecario)\b", c):
        return 65

    # Consulting
    if re.search(r"\b(consulting|consultoría|globant|softtek|accenture|deloitte|ey|pwc|kpmg)\b", c):
        return 40

    return 50


def recruiter_outreach(job_url, conn):
    """Score por outreach de reclutador (5% del total). [0-100]"""
    if not job_url:
        return 0
    row = conn.execute(
        "SELECT COUNT(*) FROM linkedin_messages WHERE job_url = ? AND is_recruiter = 1",
        (job_url,)
    ).fetchone()
    return 100 if row and row[0] > 0 else 0


def score_job(job, profile, conn):
    """Calcula score compuesto 0-100 para un job."""
    weights = profile.get("weights", {
        "title_match": 0.25,
        "seniority_match": 0.20,
        "skills_match": 0.25,
        "location_match": 0.10,
        "company_relevance": 0.15,
        "recruiter_outreach": 0.05,
    })

    t_score = title_match(job["title"], profile)
    s_score = seniority_match(job["title"], job.get("description", ""), profile)
    k_score = skills_match(job["title"], job.get("description", ""), profile)
    l_score = location_match(job.get("location", ""), profile)
    c_score = company_relevance(job.get("company", ""), profile)
    r_score = recruiter_outreach(job.get("job_url", ""), conn)

    final = (
        t_score * weights["title_match"]
        + s_score * weights["seniority_match"]
        + k_score * weights["skills_match"]
        + l_score * weights["location_match"]
        + c_score * weights["company_relevance"]
        + r_score * weights["recruiter_outreach"]
    )

    if final >= 80:
        fit = "excellent"
    elif final >= 60:
        fit = "good"
    elif final >= 40:
        fit = "fair"
    else:
        fit = "poor"

    details = json.dumps({
        "title_score": t_score,
        "seniority_score": s_score,
        "skills_score": k_score,
        "location_score": l_score,
        "company_score": c_score,
        "recruiter_score": r_score,
    })

    return {
        "job_url": job["job_url"],
        "score": round(final, 1),
        "profile_fit": fit,
        "title_score": t_score,
        "seniority_score": s_score,
        "skills_score": k_score,
        "location_score": l_score,
        "company_score": c_score,
        "match_details": details,
    }


def score_to_db(force=False):
    """Scoring incremental o forzado."""
    profile = load_profile()
    conn = get_connection()
    ensure_schema(conn)

    if force:
        jobs = conn.execute("SELECT * FROM jobs").fetchall()
        conn.execute("DELETE FROM job_scores")
    else:
        jobs = conn.execute("""
            SELECT j.* FROM jobs j
            LEFT JOIN job_scores js ON j.job_url = js.job_url
            WHERE js.job_url IS NULL
        """).fetchall()

    if not jobs:
        print("[profile_matcher] No hay jobs nuevos para scorear.", file=sys.stderr)
        conn.close()
        return

    count = 0
    for job in jobs:
        result = score_job(dict(job), profile, conn)
        conn.execute("""
            INSERT OR REPLACE INTO job_scores
                (job_url, score, profile_fit, title_score, seniority_score,
                 skills_score, location_score, company_score, match_details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result["job_url"], result["score"], result["profile_fit"],
            result["title_score"], result["seniority_score"],
            result["skills_score"], result["location_score"],
            result["company_score"], result["match_details"],
        ))
        count += 1

    conn.commit()
    stats = conn.execute("""
        SELECT COUNT(*) as total, ROUND(AVG(score), 1) as avg_score,
               MAX(score) as max_score, MIN(score) as min_score
        FROM job_scores
    """).fetchone()
    print(f"[profile_matcher] Scoreados: {count} jobs", file=sys.stderr)
    print(f"[profile_matcher] Stats: total={stats['total']} avg={stats['avg_score']} "
          f"max={stats['max_score']} min={stats['min_score']}", file=sys.stderr)
    conn.close()


def show_url(url):
    """Muestra desglose de score para una URL específica."""
    profile = load_profile()
    conn = get_connection()
    ensure_schema(conn)

    job = conn.execute("SELECT * FROM jobs WHERE job_url = ?", (url,)).fetchone()
    if not job:
        print(f"[profile_matcher] No se encontró job con URL: {url}", file=sys.stderr)
        conn.close()
        return

    result = score_job(dict(job), profile, conn)

    print(f"\n{'='*60}")
    print(f"  {job['title']} @ {job['company']}")
    print(f"  {job['location']} | {job['source']}")
    print(f"{'='*60}")
    print(f"  Score final:      {result['score']:>5} / 100")
    print(f"  Profile fit:      {result['profile_fit']}")
    print(f"{'─'*60}")
    print(f"  Title match:      {result['title_score']:>5} * 0.25 = {result['title_score']*0.25:>5.1f}")
    print(f"  Seniority match:  {result['seniority_score']:>5} * 0.20 = {result['seniority_score']*0.20:>5.1f}")
    print(f"  Skills match:     {result['skills_score']:>5} * 0.25 = {result['skills_score']*0.25:>5.1f}")
    print(f"  Location match:   {result['location_score']:>5} * 0.10 = {result['location_score']*0.10:>5.1f}")
    print(f"  Company match:    {result['company_score']:>5} * 0.15 = {result['company_score']*0.15:>5.1f}")
    print(f"  Recruiter match:  {result.get('recruiter_score', 0):>5} * 0.05 = {result.get('recruiter_score', 0)*0.05:>5.1f}")
    print(f"{'='*60}")

    conn.close()


def list_top(n=10):
    """Lista top-N scores de la DB."""
    conn = get_connection()
    ensure_schema(conn)

    rows = conn.execute("""
        SELECT j.title, j.company, j.location, j.job_url, js.score, js.profile_fit
        FROM job_scores js
        JOIN jobs j ON js.job_url = j.job_url
        ORDER BY js.score DESC
        LIMIT ?
    """, (n,)).fetchall()

    if not rows:
        print("[profile_matcher] No hay scores en la DB. Ejecuta --to-db primero.", file=sys.stderr)
        conn.close()
        return

    print(f"\n{'Top ' + str(n) + ' ofertas mejor puntuadas':^80}")
    print(f"{'#'*80}")
    print(f"{'Score':<7} {'Fit':<10} {'Título':<35} {'Empresa':<20}")
    print(f"{'-'*80}")
    for i, row in enumerate(rows, 1):
        fit_icon = {"excellent": "🟢", "good": "🔵", "fair": "🟡", "poor": "🔴"}
        icon = fit_icon.get(row["profile_fit"], "⚪")
        print(f"  {row['score']:<5} {icon} {row['profile_fit']:<8} {row['title'][:33]:<35} {row['company'][:18]:<20}")
    print(f"{'='*80}")
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Motor de scoring de ofertas")
    parser.add_argument("--to-db", action="store_true", help="Scoring incremental a DB")
    parser.add_argument("--force", action="store_true", help="Re-scoring completo")
    parser.add_argument("--url", type=str, help="Ver score de una URL específica")
    parser.add_argument("--list-top", type=int, default=0, help="Mostrar top-N scores")
    args = parser.parse_args()

    if args.url:
        show_url(args.url)
    elif args.list_top:
        list_top(args.list_top)
    elif args.to_db:
        score_to_db(force=args.force)
    else:
        # Default: mostrar top 10
        list_top(10)


if __name__ == "__main__":
    main()