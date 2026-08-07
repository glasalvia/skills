#!/usr/bin/env python3
"""Pipeline de postulaciones: CRUD + reporte."""

import sys
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from db_setup import get_connection, upgrade_schema

PARENT = Path(__file__).resolve().parent
COVER_LETTER_DIR = PARENT / "cover_letters"
VALID_STATUSES = ["pending", "applied", "phone_screen", "interview", "technical", "offer", "rejected", "withdrawn"]


def list_pending(threshold=60):
    """Lista ofertas scoreadas sin postular."""
    conn = get_connection()
    upgrade_schema(conn)
    rows = conn.execute("""
        SELECT j.title, j.company, j.location, j.job_url, js.score, js.profile_fit
        FROM job_scores js
        JOIN jobs j ON js.job_url = j.job_url
        WHERE js.score >= ? AND js.job_url NOT IN (
            SELECT job_url FROM applications
        )
        ORDER BY js.score DESC
    """, (threshold,)).fetchall()

    if not rows:
        print("[apply_tracker] No hay ofertas pendientes con score >= {}.", file=sys.stderr)
        conn.close()
        return

    print(f"{'Score':<7} {'Fit':<10} {'Título':<35} {'Empresa':<20} {'Ubicación':<20}")
    print("-" * 95)
    fit_icons = {"excellent": "🟢", "good": "🔵", "fair": "🟡", "poor": "🔴"}
    for r in rows:
        icon = fit_icons.get(r["profile_fit"], "⚪")
        print(f"{r['score']:<5} {icon} {r['profile_fit']:<8} {r['title'][:33]:<35} {(r['company'] or '')[:18]:<20} {(r['location'] or '')[:18]:<20}")
    conn.close()


def list_all():
    """Lista todas las postulaciones."""
    conn = get_connection()
    upgrade_schema(conn)
    rows = conn.execute("""
        SELECT a.id, j.title, j.company, a.status, a.applied_at
        FROM applications a
        JOIN jobs j ON a.job_url = j.job_url
        ORDER BY a.applied_at DESC
    """).fetchall()

    if not rows:
        print("[apply_tracker] No hay postulaciones registradas.", file=sys.stderr)
        conn.close()
        return

    status_icons = {
        "pending": "⏳", "applied": "📤", "phone_screen": "📞",
        "interview": "🎯", "technical": "💻", "offer": "🎉",
        "rejected": "❌", "withdrawn": "🛑",
    }
    print(f"{'ID':<5} {'Título':<35} {'Empresa':<20} {'Estado':<18} {'Fecha':<12}")
    print("-" * 95)
    for r in rows:
        icon = status_icons.get(r["status"], "❓")
        fecha = (r["applied_at"] or "")[:10]
        print(f"{r['id']:<5} {r['title'][:33]:<35} {(r['company'] or '')[:18]:<20} {icon} {r['status']:<15} {fecha:<12}")
    conn.close()


def register(url, portal="linkedin", notes="", cover_letter=False):
    """Registra una postulación."""
    conn = get_connection()
    upgrade_schema(conn)

    # Obtener job de DB
    job = conn.execute(
        "SELECT title, company, job_url FROM jobs WHERE job_url = ?",
        (url,)
    ).fetchone()
    if not job:
        print(f"[apply_tracker] Job no encontrado en DB: {url}", file=sys.stderr)
        conn.close()
        return

    # Check duplicado
    existing = conn.execute(
        "SELECT id FROM applications WHERE job_url = ?", (url,)
    ).fetchone()
    if existing:
        print(f"[apply_tracker] Ya registrado: {job['title']} (id={existing['id']})", file=sys.stderr)
        conn.close()
        return

    now = datetime.now().isoformat()
    cl_path = None

    if cover_letter:
        COVER_LETTER_DIR.mkdir(exist_ok=True)
        safe_name = f"{job['job_url'].split('/')[-1]}_{job['company'][:20].replace(' ', '_')}"
        cl_path = str(COVER_LETTER_DIR / f"{safe_name}.md")
        try:
            subprocess.run(
                ["python3", "cover_letter_gen.py", "--url", job["job_url"], "--output", cl_path],
                cwd=str(WORKSPACE), check=True, timeout=60,
                capture_output=True, text=True,
            )
            print(f"[apply_tracker] Cover letter generada: {cl_path}", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"[apply_tracker] Error generando cover letter: {e.stderr}", file=sys.stderr)
            cl_path = None

    conn.execute("""
        INSERT INTO applications (job_url, portal_url, portal_type, status, cover_letter, notes, applied_at)
        VALUES (?, ?, ?, 'pending', ?, ?, ?)
    """, (url, url, portal, cl_path, notes, now))
    conn.commit()
    print(f"[apply_tracker] Postulación registrada: {job['title']} @ {job['company']} (pending)", file=sys.stderr)
    conn.close()


def update_status(app_id, status):
    """Actualiza estado de una postulación."""
    if status not in VALID_STATUSES:
        print(f"[apply_tracker] Estado inválido: {status}. Válidos: {', '.join(VALID_STATUSES)}", file=sys.stderr)
        return

    conn = get_connection()
    upgrade_schema(conn)

    row = conn.execute("SELECT id FROM applications WHERE id = ?", (app_id,)).fetchone()
    if not row:
        print(f"[apply_tracker] Postulación id={app_id} no encontrada.", file=sys.stderr)
        conn.close()
        return

    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE applications SET status = ?, updated_at = ? WHERE id = ?",
        (status, now, app_id)
    )
    conn.commit()
    print(f"[apply_tracker] Postulación id={app_id} → {status}", file=sys.stderr)
    conn.close()


def report():
    """Reporte del pipeline."""
    conn = get_connection()
    upgrade_schema(conn)

    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM applications GROUP BY status ORDER BY status"
    ).fetchall()

    status_order = ["pending", "applied", "phone_screen", "interview", "technical", "offer", "rejected", "withdrawn"]
    count_by_status = {r["status"]: r["cnt"] for r in rows}
    total = sum(count_by_status.values())

    print("\nPipeline Report")
    print("=" * 40)
    for s in status_order:
        cnt = count_by_status.get(s, 0)
        print(f"  {s.replace('_', ' ').title():.<20} {cnt}")
    print("─" * 40)
    print(f"  {'Total':.<20} {total}")
    print()

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Pipeline de postulaciones")
    parser.add_argument("--list-pending", action="store_true", help="Ofertas sin postular con score > 60")
    parser.add_argument("--list-all", action="store_true", help="Todas las postulaciones")
    parser.add_argument("--register", action="store_true", help="Registrar postulación")
    parser.add_argument("--url", type=str, help="URL de la oferta")
    parser.add_argument("--portal", type=str, default="linkedin", help="Portal (linkedin, indeed, etc)")
    parser.add_argument("--notes", type=str, default="", help="Notas de la postulación")
    parser.add_argument("--cover-letter", action="store_true", help="Generar cover letter")
    parser.add_argument("--status", type=str, help="Nuevo estado")
    parser.add_argument("--id", type=int, help="ID de postulación")
    parser.add_argument("--report", action="store_true", help="Reporte de pipeline")
    args = parser.parse_args()

    if args.list_pending:
        list_pending()
    elif args.list_all:
        list_all()
    elif args.register:
        if not args.url:
            print("[apply_tracker] --url es requerido con --register", file=sys.stderr)
            sys.exit(1)
        register(args.url, args.portal, args.notes, args.cover_letter)
    elif args.id and args.status:
        update_status(args.id, args.status)
    elif args.report:
        report()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()