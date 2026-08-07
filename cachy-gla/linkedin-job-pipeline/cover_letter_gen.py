#!/usr/bin/env python3
"""Generador de cover letters personalizadas vía Ollama Qwen local."""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass

import yaml

_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DIR, "linkedin_jobs.db")
PROFILE_PATH = os.path.join(_DIR, "profile.yaml")
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen3.6-35b-mtp"
FALLBACK_MODEL = "qwen2.5-coder:7b"


@dataclass
class Profile:
    name: str
    title: str
    seniority: str
    years: int
    summary: str


def load_profile() -> Profile:
    """Carga perfil del candidato desde profile.yaml."""
    with open(PROFILE_PATH) as f:
        data = yaml.safe_load(f)
    c = data["candidate"]
    skills_str = ", ".join(c.get("skills", {}).get("core", []))
    locations_str = ", ".join(c.get("locations", {}).get("preferred", []))
    summary = (
        f"{c['name']} - {c.get('current_title', 'N/A')}, "
        f"{c.get('years_experience', 0)} años de experiencia. "
        f"Skills: {skills_str}. Ubicaciones: {locations_str}."
    )
    return Profile(
        name=c.get("name", "Candidato"),
        title=c.get("current_title", "N/A"),
        seniority=c.get("seniority", "senior"),
        years=c.get("years_experience", 0),
        summary=summary,
    )


def get_job_from_db(job_url: str) -> dict:
    """Obtiene job de la DB por URL."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT title, company, location, description FROM jobs WHERE job_url = ?",
        (job_url,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def list_available_jobs() -> list[dict]:
    """Lista jobs disponibles en DB para seleccionar URL."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT job_url, title, company FROM jobs ORDER BY discovered_at DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def call_ollama(model: str, messages: list[dict]) -> str:
    """Llama a Ollama API y retorna texto de respuesta."""
    payload = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data["message"]["content"]
    except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"Error llamando a Ollama ({model}): {e}")


def build_ollama_prompt(job: dict, profile: Profile, lang: str) -> list[dict]:
    """Construye mensajes para Ollama."""
    lang_instruction = (
        "Eres un asistente que genera cover letters profesionales en español."
        if lang == "es"
        else "You are an assistant that generates professional cover letters in English."
    )

    system_prompt = (
        f"{lang_instruction} La carta debe ser formal, destacar las "
        "habilidades del candidato que coinciden con el puesto, "
        "y no superar 300 palabras."
    )

    user_prompt = (
        f"Puesto: {job['title']}\n"
        f"Empresa: {job['company']}\n"
        f"Ubicación: {job.get('location', 'No especificada')}\n"
        f"Descripción:\n{job.get('description', 'Sin descripción')[:2000]}\n\n"
        f"Perfil del candidato:\n{profile.summary}\n\n"
        "Genera una cover letter personalizada para postularme a este puesto."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def main():
    parser = argparse.ArgumentParser(description="Generador de cover letters vía Ollama")
    parser.add_argument("--url", help="URL del job en LinkedIn")
    parser.add_argument("--output", help="Archivo de salida (default: stdout)")
    parser.add_argument("--lang", default="es", choices=["es", "en"], help="Idioma")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar contexto sin generar")
    parser.add_argument("--list-jobs", action="store_true", help="Listar jobs disponibles")
    args = parser.parse_args()

    if args.list_jobs:
        jobs = list_available_jobs()
        if not jobs:
            print("No hay jobs en la base de datos.", file=sys.stderr)
            sys.exit(1)
        print("Jobs disponibles (URL → título):")
        for j in jobs:
            print(f"  {j['job_url']}")
            print(f"    → {j['title']} - {j['company']}")
        return

    if not args.url:
        parser.print_help()
        sys.exit(1)

    profile = load_profile()
    job = get_job_from_db(args.url)
    if job is None:
        print(f"Error: job no encontrado en DB: {args.url}", file=sys.stderr)
        sys.exit(1)

    messages = build_ollama_prompt(job, profile, args.lang)

    if args.dry_run:
        print("=== SYSTEM PROMPT ===")
        print(messages[0]["content"])
        print("\n=== USER PROMPT ===")
        print(messages[1]["content"])
        return

    try:
        text = call_ollama(DEFAULT_MODEL, messages)
    except RuntimeError:
        text = call_ollama(FALLBACK_MODEL, messages)

    if args.output:
        with open(args.output, "w") as f:
            f.write(text.strip() + "\n")
        print(f"Cover letter guardada en {args.output}")
    else:
        print(text.strip())


if __name__ == "__main__":
    main()