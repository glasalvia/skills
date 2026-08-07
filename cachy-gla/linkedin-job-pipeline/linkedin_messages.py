#!/usr/bin/env python3
"""Monitor de mensajes entrantes de LinkedIn vía gog CLI."""

import os
import subprocess
import re
import sys
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_setup import get_connection, upgrade_schema

_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DIR, "linkedin_jobs.db")
GOG_BIN = "/usr/bin/gog"
EMAIL = "glasalviacalio@gmail.com"
RECRUITER_KEYWORDS = [
    "recruiter", "recruiting", "talent acquisition", "hiring manager",
    "opportunity", "role", "position", "hiring", "interview",
    "your profile", "your background", "your experience",
    "we are looking for", "we're hiring", "join our team",
    "i came across your profile", "i found your profile",
    "open position", "would you be interested",
]


def search_messages(max_results=20):
    """Busca mensajes de LinkedIn via gog."""
    cmd = [
        GOG_BIN, "gmail", "search",
        'from:linkedinmail@linkedin.com "You have a new message"',
        "--max", str(max_results),
        "--no-input",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"[linkedin_messages] Error en gog search: {result.stderr}", file=sys.stderr)
        return []
    return parse_gog_table(result.stdout)


def parse_gog_table(text):
    """Parsea la tabla de resultados de gog."""
    lines = text.strip().split("\n")
    messages = []
    # Skip header lines (usually first 3-4 lines)
    data_start = 0
    for i, line in enumerate(lines):
        if line.startswith("+") or line.startswith("|"):
            continue
        if line.strip() and not line.startswith("ID"):
            data_start = i
            break

    for line in lines[data_start:]:
        line = line.strip()
        if not line or line.startswith("+") or line.startswith("|"):
            continue
        # Parse gog table format: ID | From | Subject | Date | Snippet
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            msg = {
                "message_id": parts[0].strip(),
                "from": parts[1].strip() if len(parts) > 1 else "",
                "subject": parts[2].strip() if len(parts) > 2 else "",
                "date": parts[3].strip() if len(parts) > 3 else "",
                "snippet": parts[4].strip() if len(parts) > 4 else "",
            }
            # Extract message_id from first column (might be "ID" or numeric)
            msg_id_match = re.search(r"\d+", parts[0])
            if msg_id_match:
                msg["message_id"] = msg_id_match.group()
            if msg.get("message_id"):
                messages.append(msg)
    return messages


def read_message(message_id):
    """Lee el cuerpo completo de un mensaje via gog."""
    cmd = [GOG_BIN, "gmail", "read", str(message_id), "--no-input"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"[linkedin_messages] Error leyendo mensaje {message_id}: {result.stderr}", file=sys.stderr)
        return ""
    return result.stdout


def extract_sender_info(body):
    """Extrae remitente, headline, empresa del cuerpo del mensaje."""
    result = {"from_name": "", "from_headline": "", "from_company": ""}

    # Try to find LinkedIn message header patterns
    # Format: "Nombre Apellido\nHeadline at Company\n..."
    lines = body.split("\n")
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        # First non-empty line is often the name
        if line_stripped and not result["from_name"]:
            # Check if it looks like a name (not a URL, email, or header)
            if not re.search(r"@|http|^Sent:|^From:|^To:|^Subject:|^Date:|^Reply|InMail|Message", line_stripped):
                result["from_name"] = line_stripped
        elif result["from_name"] and not result["from_headline"]:
            # Next line might be headline
            if line_stripped and "at " in line_stripped:
                parts = line_stripped.split(" at ", 1)
                result["from_headline"] = parts[0].strip()
                result["from_company"] = parts[1].strip() if len(parts) > 1 else ""
                break
            elif line_stripped and not re.search(r"@|http|^Sent:|^From:", line_stripped):
                result["from_headline"] = line_stripped

    return result


def extract_job_url(body):
    """Extrae URL de LinkedIn Jobs del cuerpo del mensaje."""
    patterns = [
        r"https?://(?:www\.)?linkedin\.com/jobs/view/\d+",
        r"https?://(?:www\.)?linkedin\.com/jobs/collections/recommended/\d+",
    ]
    for pattern in patterns:
        match = re.search(pattern, body)
        if match:
            return match.group(0)
    return None


def is_recruiter(body):
    """Detecta si el mensaje es de un reclutador por keywords."""
    body_lower = body.lower()
    matches = sum(1 for kw in RECRUITER_KEYWORDS if kw in body_lower)
    return matches >= 2


def parse_date(date_str):
    """Parsea fecha de gog a timestamp."""
    try:
        # Try common date formats
        for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%d/%m/%Y", "%Y-%m-%d"]:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
    except Exception:
        pass
    return datetime.now()


def insert_message(conn, msg):
    """Inserta un mensaje en linkedin_messages."""
    conn.execute("""
        INSERT OR IGNORE INTO linkedin_messages
            (from_name, from_headline, from_company, subject, body, job_url, is_recruiter, received_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        msg.get("from_name", ""),
        msg.get("from_headline", ""),
        msg.get("from_company", ""),
        msg.get("subject", ""),
        msg.get("body", ""),
        msg.get("job_url"),
        msg.get("is_recruiter", False),
        msg.get("received_at"),
    ))
    conn.commit()


def fetch_messages():
    """Busca y almacena mensajes nuevos."""
    conn = get_connection()
    upgrade_schema(conn)

    messages = search_messages()
    if not messages:
        print("[linkedin_messages] No se encontraron mensajes nuevos.", file=sys.stderr)
        conn.close()
        return

    count = 0
    for msg in messages:
        body = read_message(msg["message_id"])
        if not body:
            continue

        sender = extract_sender_info(body)
        job_url = extract_job_url(body)
        recruiter = is_recruiter(body)

        msg_data = {
            "from_name": sender["from_name"] or msg.get("from", ""),
            "from_headline": sender["from_headline"],
            "from_company": sender["from_company"],
            "subject": msg.get("subject", ""),
            "body": body[:2000],  # Truncate long bodies
            "job_url": job_url,
            "is_recruiter": recruiter,
            "received_at": parse_date(msg.get("date", "")).isoformat(),
        }
        insert_message(conn, msg_data)
        count += 1
        print(f"[linkedin_messages] Almacenado: {msg_data['from_name']} - {msg_data.get('subject', '')[:60]}")

    print(f"[linkedin_messages] Total mensajes almacenados: {count}", file=sys.stderr)
    conn.close()


def list_messages(recruiters_only=False, since_days=None):
    """Lista mensajes almacenados."""
    conn = get_connection()
    query = "SELECT id, from_name, from_headline, from_company, subject, is_recruiter, received_at FROM linkedin_messages"
    conditions = []
    params = []

    if recruiters_only:
        conditions.append("is_recruiter = 1")
    if since_days:
        since_date = (datetime.now() - timedelta(days=since_days)).isoformat()
        conditions.append("received_at >= ?")
        params.append(since_date)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY received_at DESC"

    rows = conn.execute(query, params).fetchall()
    if not rows:
        print("[linkedin_messages] No hay mensajes almacenados.")
        conn.close()
        return

    print(f"{'ID':<5} {'Remitente':<25} {'Empresa':<20} {'Reclutador':<12} {'Asunto':<50}")
    print("-" * 120)
    for row in rows:
        recruiter_tag = "🟢 SI" if row["is_recruiter"] else "  NO"
        print(f"{row['id']:<5} {row['from_name']:<25} {row['from_company'] or '':<20} {recruiter_tag:<12} {(row['subject'] or '')[:50]:<50}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Monitor de mensajes LinkedIn")
    parser.add_argument("--fetch", action="store_true", help="Buscar y almacenar mensajes nuevos")
    parser.add_argument("--list", action="store_true", help="Listar mensajes almacenados")
    parser.add_argument("--recruiters", action="store_true", help="Solo mensajes de reclutadores")
    parser.add_argument("--since", type=int, default=None, help="Días hacia atrás")
    args = parser.parse_args()

    if args.fetch:
        fetch_messages()
    elif args.list:
        list_messages(recruiters_only=args.recruiters, since_days=args.since)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()