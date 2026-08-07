#!/usr/bin/env python3
"""DB unificada de empleos — creación y utilidades SQLite."""

import os
import sqlite3
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DIR, "linkedin_jobs.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            source TEXT NOT NULL,
            job_url TEXT UNIQUE NOT NULL,
            date_posted TEXT,
            description TEXT,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(job_url)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_discovered ON jobs(discovered_at)")
    conn.commit()
    return conn


def upgrade_schema(conn):
    """Agrega columnas y tablas nuevas al schema si no existen."""
    # Columnas opcionales en jobs
    for col in ("seniority", "remote", "salary_min", "salary_max", "salary_currency"):
        try:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT")
        except Exception:
            pass  # ya existe

    # Remapear remote a BOOLEAN (SQLite no cambia tipo en ALTER, pero marcamos semántica)
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS job_scores (
            job_url TEXT PRIMARY KEY REFERENCES jobs(job_url),
            score REAL,
            profile_fit TEXT CHECK(profile_fit IN ('excellent','good','fair','poor')),
            title_score REAL,
            seniority_score REAL,
            skills_score REAL,
            location_score REAL,
            company_score REAL,
            match_details TEXT,
            scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    except Exception:
        pass

    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS linkedin_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_name TEXT NOT NULL,
            from_headline TEXT,
            from_company TEXT,
            subject TEXT,
            body TEXT,
            job_url TEXT,
            is_recruiter BOOLEAN DEFAULT 0,
            received_at TIMESTAMP,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    except Exception:
        pass

    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_url TEXT NOT NULL REFERENCES jobs(job_url),
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','applied','phone_screen','interview','technical','offer','rejected','withdrawn')),
            portal_url TEXT,
            portal_type TEXT,
            cover_letter TEXT,
            notes TEXT,
            applied_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    except Exception:
        pass

    conn.commit()


def insert_job(conn, job):
    """Inserta un job si no existe (dedup por job_url). Retorna True si se insertó."""
    import sys as _sys
    try:
        conn.execute("""
            INSERT OR IGNORE INTO jobs (job_id, title, company, location, source, job_url, date_posted, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.get("job_id", ""),
            job["title"],
            job.get("company", ""),
            job.get("location", ""),
            job["source"],
            job["job_url"],
            job.get("date_posted", ""),
            job.get("description", "")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error insertando job: {e}", file=_sys.stderr)
        return False


def insert_job_with_extras(conn, job):
    """Inserta un job con campos opcionales extendidos (seniority, remote, salary)."""
    import sys as _sys
    try:
        conn.execute("""
            INSERT OR IGNORE INTO jobs (
                job_id, title, company, location, source, job_url,
                date_posted, description, seniority, remote, salary_min, salary_max, salary_currency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.get("job_id", ""),
            job["title"],
            job.get("company", ""),
            job.get("location", ""),
            job["source"],
            job["job_url"],
            job.get("date_posted", ""),
            job.get("description", ""),
            job.get("seniority", None),
            str(job.get("remote", False)),
            job.get("salary_min", None),
            job.get("salary_max", None),
            job.get("salary_currency", None)
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error insertando job con extras: {e}", file=_sys.stderr)
        return False


def get_db_stats(conn):
    """Retorna un dict con estadísticas de la DB."""
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    by_source_rows = conn.execute(
        "SELECT source, COUNT(*) as cnt FROM jobs GROUP BY source"
    ).fetchall()
    by_source = {r["source"]: r["cnt"] for r in by_source_rows}

    today_str = conn.execute("SELECT DATE('now')").fetchone()[0]
    new_today = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE DATE(discovered_at) = ?",
        (today_str,)
    ).fetchone()[0]

    avg_score_row = conn.execute("SELECT AVG(score) FROM job_scores").fetchone()
    avg_score = avg_score_row[0] if avg_score_row[0] is not None else None

    total_scores = conn.execute("SELECT COUNT(*) FROM job_scores").fetchone()[0]

    return {
        "total_jobs": total,
        "by_source": by_source,
        "new_today": new_today,
        "avg_score": avg_score,
        "total_scores": total_scores
    }


if __name__ == "__main__":
    conn = init_db()
    upgrade_schema(conn)
    print(f"[db_setup] DB lista en {DB_PATH}", file=sys.stderr)

    stats = get_db_stats(conn)
    print(f"[db_setup] Total jobs: {stats['total_jobs']}", file=sys.stderr)
    print(f"[db_setup] Por fuente: {stats['by_source']}", file=sys.stderr)
    print(f"[db_setup] Nuevos hoy: {stats['new_today']}", file=sys.stderr)
    print(f"[db_setup] Score promedio: {stats['avg_score']}", file=sys.stderr)
    print(f"[db_setup] Total scores: {stats['total_scores']}", file=sys.stderr)
    conn.close()
