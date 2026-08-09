#!/bin/bash
# weekly_scrape.sh — Scraping semanal de ofertas LinkedIn vía JobSpy
# Ejecución: sábados 08:00 ART
# Depende de: python3, jobspy_scraper.py, linkedin_jobs.db

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="/tmp/weekly_scrape.log"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

echo "[$TIMESTAMP] Iniciando scraping semanal..." >> "$LOG_FILE"

# Términos de búsqueda (Data/Platform roles)
SEARCH_TERMS=(
    "data engineer"
    "platform engineer"
    "data architect"
    "data platform engineer"
    "head of data"
    "data director"
    "cloud architect"
    "data infrastructure"
    "data platform"
    "big data engineer"
)

# Ubicaciones relevantes
LOCATIONS=(
    "Remote"
    "Argentina"
    "Spain"
    "Mexico"
    "Colombia"
    "Chile"
)

for search in "${SEARCH_TERMS[@]}"; do
    for location in "${LOCATIONS[@]}"; do
        echo "[$TIMESTAMP] Buscando: $search en $location" >> "$LOG_FILE"
        python3 "$SCRIPT_DIR/jobspy_scraper.py" \
            --search "$search" \
            --location "$location" \
            --max 30 \
            --hours 168 \
            --to-db 2>> "$LOG_FILE"
        sleep 3  # Pausa entre requests para evitar rate limiting
    done
done

echo "[$TIMESTAMP] Scraping semanal completado." >> "$LOG_FILE"