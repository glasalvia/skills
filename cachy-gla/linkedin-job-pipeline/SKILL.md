---
name: "linkedin-job-pipeline"
description: "Pipeline Data/Platform jobs: scraping, scoring perfil, digest Telegram, tracking postulaciones"
---

# LinkedIn Job Pipeline — SKILL.md

Pipeline integral de consolidación, priorización y seguimiento de ofertas Data/Platform Engineering para Gonzalo La Salvia (Data Platform Sr Manager).

## Arquitectura (cinco capas)

```
Capa 1 (diaria):       gog → linkedin_alert_parser.py → linkedin_jobs.db
Capa 2 (semanal):      python-jobspy → jobspy_scraper.py → linkedin_jobs.db
Capa 3 (on-demand):    profile_matcher.py → job_scores.db        ← NUEVA
Capa 4 (diaria):       daily_digest.py → Telegram                ← NUEVA
Capa 5 (on-demand):    apply_tracker.py → applications.db        ← NUEVA
```

## Archivos (skills/linkedin-job-pipeline/)

| Archivo | Rol |
|---------|-----|
| `linkedin_alert_parser.py` | Busca emails `jobalerts-noreply@linkedin.com` vía gog CLI, parsea jobs, inserta en DB |
| `jobspy_scraper.py` | Scraping multi-board (LinkedIn, Indeed, Google Jobs) con python-jobspy |
| `db_setup.py` | Módulo reutilizable: init_db(), insert_job(), DB_PATH |
| `profile_matcher.py` | Evalúa cada oferta contra el perfil del usuario, asigna score 0-100 |
| `profile.yaml` | Perfil del candidato: título, seniority, skills, ubicaciones preferidas |
| `daily_digest.py` | Ejecuta Capa 1 + scoring + envía top-N por Telegram |
| `linkedin_messages.py` | Monitorea mensajes entrantes de LinkedIn vía gog (notificaciones email) |
| `apply_tracker.py` | Gestiona pipeline de postulaciones: registrar, listar, generar cover letter |
| `cover_letter_gen.py` | Genera cover letter personalizada vía Ollama Qwen local |
| `linkedin_jobs.db` | Base SQLite unificada (jobs + scores + messages + applications) |
| `generate_report.py` | Genera informe de mercado Markdown/HTML (existente) |
| `cover_letters/` | Directorio de cover letters generadas |
| `data/` | Archivos auxiliares (DB vacía residual) |

## DB Schema (linkedin_jobs.db)

```sql
-- Tabla existente: ofertas detectadas
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    source TEXT NOT NULL,          -- linkedin_email, linkedin, indeed, google
    job_url TEXT UNIQUE NOT NULL,
    date_posted TEXT,
    description TEXT,
    seniority TEXT,                -- junior, mid, senior, lead
    salary_min REAL,
    salary_max REAL,
    salary_currency TEXT,
    remote BOOLEAN DEFAULT 0,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_jobs_url ON jobs(job_url);
CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_jobs_discovered ON jobs(discovered_at);

-- NUEVA: puntuación de matching contra perfil
CREATE TABLE job_scores (
    job_url TEXT PRIMARY KEY REFERENCES jobs(job_url),
    score REAL NOT NULL,
    profile_fit TEXT NOT NULL CHECK(profile_fit IN ('excellent','good','fair','poor')),
    title_score REAL,
    seniority_score REAL,
    skills_score REAL,
    location_score REAL,
    company_score REAL,
    match_details TEXT,            -- JSON con desglose
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NUEVA: mensajes entrantes de LinkedIn
CREATE TABLE linkedin_messages (
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
);

-- NUEVA: tracking de postulaciones
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_url TEXT NOT NULL REFERENCES jobs(job_url),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending','applied','phone_screen','interview','technical','offer','rejected','withdrawn')),
    portal_url TEXT,
    portal_type TEXT,               -- linkedin, greenhouse, lever, workday, company_site, other
    cover_letter TEXT,
    notes TEXT,
    applied_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Perfil del Candidato (profile.yaml)

```yaml
# Perfil de Gonzalo La Salvia — usado por profile_matcher.py
candidate:
  name: Gonzalo La Salvia
  current_title: Data Platform Sr Manager
  seniority: lead                     # junior | mid | senior | lead
  years_experience: 15
  skills:
    core:
      - data engineering
      - data platform
      - cloud architecture
      - spark
      - python
      - sql
      - aws
      - databricks
      - snowflake
      - airflow
      - kafka
      - terraform
      - kubernetes
    secondary:
      - docker
      - gitlab ci
      - dbt
      - redshift
      - bigquery
      - delta lake
      - lakehouse
  industries:
    preferred:
      - technology
      - fintech
      - data & analytics
      - cloud services
    acceptable:
      - banking
      - consulting
      - e-commerce
      - healthcare
  locations:
    primary: Remote, Argentina
    secondary:
      - Remote, LatAm
      - Remote, US
      - Buenos Aires, Argentina
  salary_expectation:
    min_usd: 7000
    preferred_usd: 9000
  companies_target:
    - FAANG
    - big tech
    - data-first companies
    - well-funded startups (Series B+)
  avoid_companies:
    - outsourcers low value
    - bodyshops
    - non-tech industries
  # Ponderadores para score (sum = 1.0)
  weights:
    title_match: 0.25
    seniority_match: 0.20
    skills_match: 0.25
    location_match: 0.10
    company_relevance: 0.15
    recruiter_outreach: 0.05
```

## Uso

```bash
# Todos los comandos se ejecutan desde el directorio del skill:
cd skills/linkedin-job-pipeline

# Capa 1 — Alertas email (diario)
python linkedin_alert_parser.py --to-db

# Capa 2 — Scraping ampliado (semanal)
python jobspy_scraper.py --search "data engineer" --location "Argentina" --max 20 --to-db

# Capa 3 — Profile matching (después de Capa 1 o 2)
python profile_matcher.py --to-db

# Ver matching de una oferta específica
python profile_matcher.py --url "https://linkedin.com/jobs/view/123"

# Capa 4 — Digest diario (ejecuta Capa 1 + scoring + envía a Telegram)
python daily_digest.py
python daily_digest.py --top 10                          # top-10 en vez de top-5
python daily_digest.py --dry-run                         # solo stdout, no Telegram

# Capa 5 — Postulaciones
python apply_tracker.py --list-pending                   # ofertas prioritarias sin postular
python apply_tracker.py --list-all                       # todas las postulaciones
python apply_tracker.py --register <job_url>             # registrar postulación manual
python apply_tracker.py --status <job_url> --set interview  # actualizar estado

# Cover letter
python cover_letter_gen.py --url "https://linkedin.com/jobs/view/123"
python cover_letter_gen.py --url "https://..." --output cover_letter.md

# Mensajes LinkedIn entrantes
python linkedin_messages.py --fetch                      # buscar mensajes nuevos vía gog
python linkedin_messages.py --list                       # listar mensajes detectados
python linkedin_messages.py --recruiters                 # solo reclutadores

# Consultas rápidas
sqlite3 linkedin_jobs.db "SELECT score, title, company FROM job_scores js JOIN jobs j ON js.job_url=j.job_url ORDER BY score DESC LIMIT 10"

# Reporte de mercado (existente)
python generate_report.py
python generate_report.py --html informe.html
```

## Profile Matching Engine (profile_matcher.py)

### Algoritmo de scoring

Cada oferta recibe un score compuesto 0-100 basado en:

1. **Title Match (25%)**: Coincidencia del título contra patrones del perfil
   - Exact match "Data Platform Sr Manager" → 100
   - Keyword match: "Data Platform", "Data Engineer", "Platform Engineer" → 80-95
   - Partial match: "Data", "Engineer", "Platform" isolated → 40-70
   - No match → 0

2. **Seniority Match (20%)**: Nivel del rol vs experiencia
   - Lead/Manager/Director/Head → 100 (match exacto)
   - Senior → 70
   - Mid → 30
   - Junior → 0

3. **Skills Match (25%)**: Intersección de skills del perfil vs descripción
   - Cada skill core presente suma puntos ponderados
   - Skills secundarios suman la mitad
   - Embeddings nomic-embed-text para matching semántico en descripciones largas

4. **Location Match (10%)**: Preferencia geográfica
   - Remote, Argentina → 100
   - Remote, LatAm → 80
   - Remote, US → 60
   - Buenos Aires presencial → 50
   - Otras → 20-40

5. **Company Relevance (15%)**: Tipo de empresa
   - Tech/Data-first → 80-100
   - Fintech/Banking → 60-80
   - Consultoría → 30-50
   - Bodyshop / low-value → 0-10

6. **Recruiter Outreach (5%)**: Si hay mensaje de reclutador asociado → 100

### Ejecución

```bash
# Scoring incremental: solo ofertas sin score
python profile_matcher.py --to-db

# Re-scoring completo
python profile_matcher.py --to-db --force

# Ver una oferta
python profile_matcher.py --url "https://linkedin.com/jobs/view/123"
```

## Daily Digest (daily_digest.py)

Flujo cada ejecución:

```
1. Ejecutar linkedin_alert_parser.py --to-db           # ofertas nuevas
2. Ejecutar profile_matcher.py --to-db                  # scoring incremental
3. Consultar top-N ofertas con score > umbral (default 70)
4. Formatear mensaje Telegram
5. Enviar vía message tool (canal: telegram, target: 1797240161)
```

### Formato del mensaje Telegram

```
📊 *Digest Laboral* — DD/MM

🔥 *Prioritarias* (score 80+):
1. [Data Platform Manager] · Blend · Remote · Score: 92
   → https://linkedin.com/jobs/view/...
2. [Staff Data Engineer] · Meta · Remote, US · Score: 88
   → ...

📌 *Nuevas hoy*: 12 · *Postulaciones pendientes*: 3
```

### Ejecución

```bash
# Manual
python daily_digest.py

# Con cron (diario a las 09:00 ART)
# Ejemplo: cron kind=cron, expr="0 9 * * 1-5", tz="America/Buenos_Aires"
# Job: isolated agentTurn con message "Ejecutar daily_digest.py"
```

## LinkedIn Messages (linkedin_messages.py)

LinkedIn envía notificaciones email cuando recibís un mensaje. El parser:

1. Busca en gog: `from:linkedinmail@linkedin.com "You have a new message"`
2. Filtra por fecha reciente (últimas 24h)
3. Parsea remitente, headline, extracto del mensaje
4. Detecta si es reclutador (keywords: "recruiter", "opportunity", "role", "position", "hiring")
5. Si el mensaje menciona un job URL, lo vincula con scoring bonus (+5 puntos)
6. Almacena en `linkedin_messages`

```bash
python linkedin_messages.py --fetch
python linkedin_messages.py --list --recruiters
```

## Application Tracker (apply_tracker.py)

Gestiona el pipeline de candidatura completo:

```bash
# Listar ofertas prioritarias sin postular
python apply_tracker.py --list-pending

# Registrar postulación manual
python apply_tracker.py --register "https://linkedin.com/jobs/view/123" \
  --portal "https://jobs.greenhouse.io/blend/jobs/456" \
  --type greenhouse

# Actualizar estado
python apply_tracker.py --status "https://..." --set interview

# Reporte de pipeline
python apply_tracker.py --report
```

### Estados del pipeline

```
pending → applied → phone_screen → interview → technical → offer
                                                   ↓
                                              rejected
                                              withdrawn
```

### Cover Letter Generator (cover_letter_gen.py)

Usa Ollama Qwen local para generar cover letters personalizadas:

```bash
python cover_letter_gen.py --url "https://linkedin.com/jobs/view/123"
# → output en stdout, editable antes de postular

python cover_letter_gen.py --url "..." --output cl.md
```

Contexto inyectado al LLM:
- Descripción completa de la oferta
- Perfil del candidato (profile.yaml)
- Experiencia relevante (del perfil LinkedIn documentado)
- Instrucción: tono profesional, destacar coincidencias, max 300 palabras

## Pre-requisitos

1. **gog CLI** v0.32.0+ con keyring password `Capicua1221`
2. **python-jobspy** (--break-system-packages en Arch)
3. **sqlite3** (Python stdlib)
4. **Ollama Qwen** local (`qwen3.6-35b-mtp:latest` o similar) para cover letters
5. **nomic-embed-text** (Ollama local) para embeddings de matching semántico
6. **PyYAML** para profile.yaml: `pip install pyyaml --break-system-packages`
7. **Telegram** configurado en OpenClaw channels (chat ID: `1797240161`)
8. Alertas LinkedIn configuradas a `glasalviacalio@gmail.com`

## Alertas LinkedIn

- Keywords configurados manualmente en LinkedIn → Jobs → Job Alerts:
  - Data Engineer, Platform Engineer, Data Platform Engineer, Head Data, Data Architect
- Ubicaciones: Argentina, Remote, Latin America
- Frecuencia: diaria · Remitente: `jobalerts-noreply@linkedin.com`

## Scraping expandido (recomendado semanal)

```bash
cd /home/glasalvia/.openclaw/workspace/skills/linkedin-job-pipeline

for term in "data engineer" "platform engineer" "data architect" \
  "data platform engineer" "big data engineer" "head of data" \
  "data director" "cloud architect" "data infrastructure"; do
  for loc in "Remote" "LatAm" "Argentina" "Chile" "Uruguay" \
    "Colombia" "Mexico" "Brazil" "United States"; do
    python jobspy_scraper.py --search "$term" --location "$loc" --max 10 --to-db
  done
done
```

## Cron Jobs

### Digest diario (lunes a viernes 09:00 ART)
```json
{
  "name": "linkedin-daily-digest",
  "schedule": { "kind": "cron", "expr": "0 9 * * 1-5", "tz": "America/Buenos_Aires" },
  "payload": {
    "kind": "agentTurn",
    "message": "Ejecutar daily_digest.py desde skills/linkedin-job-pipeline/. Si hay ofertas con score >= 80, enviar digest por Telegram."
  },
  "sessionTarget": "isolated",
  "delivery": { "mode": "announce", "channel": "telegram", "to": "1797240161" }
}
```

### Scraping semanal (sábados 10:00 ART)
```json
{
  "name": "linkedin-weekly-scrape",
  "schedule": { "kind": "cron", "expr": "0 10 * * 6", "tz": "America/Buenos_Aires" },
  "payload": {
    "kind": "agentTurn",
    "message": "Ejecutar scraping expandido del LinkedIn pipeline desde skills/linkedin-job-pipeline/ y luego profile_matcher.py --to-db. Si hay ofertas con score >= 80, ejecutar daily_digest.py."
  },
  "sessionTarget": "isolated",
  "delivery": { "mode": "announce", "channel": "telegram", "to": "1797240161" }
}
```

## Notas técnicas

- **Deduplicación**: `INSERT OR IGNORE` por `job_url`
- **Scoring incremental**: profile_matcher omite ofertas ya scoreadas a menos que `--force`
- **Cover letters**: se generan localmente con Ollama, sin enviar datos a externos
- **Postulaciones en portales externos**: no se automatiza el submit (cada portal tiene su flujo), se registra manualmente y se genera cover letter asistida
- **GOG_KEYRING_PASSWORD**: `Capicua1221` — configurada en `openclaw.json` env.vars
- **Telegram**: mensajes enviados vía `message` tool interno de OpenClaw
