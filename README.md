# Skills Repository — OpenClaw Multi-Node Skill Sync

Repositorio centralizado de skills para los agentes OpenClaw en cachy-gla y Raspberry Pi.

## Estructura

```
skills/
├── shared/          # Skills presentes en AMBOS equipos
│   ├── audio-tts/        # TTS a Google Home y Alexa
│   ├── cam-entity/       # Snapshot de cámara Tapo vía HA
│   ├── dev-orchestrator/ # Orquestación de tareas de desarrollo
│   ├── facturas-ocr/     # Pipeline OCR de facturas
│   ├── gog-workspace/    # Google Workspace CLI
│   └── noticias-argentina/ # Monitoreo RSS de noticias
├── cachy-gla/       # Skills exclusivos de cachy-gla
│   ├── sdxl-image-generator/   # SDXL con RTX 5070
│   ├── music-downloader/       # Descarga MP3 vía yt-dlp
│   ├── linkedin-job-pipeline/  # Scraping LinkedIn
│   ├── notiscreen-send/        # Turing Smart Screen
│   ├── raspberry-bridge/       # SSH a Raspi (fallback)
│   └── raspi-a2a-bridge/       # Comunicación A2A
└── raspi/           # Skills exclusivos de Raspberry Pi
    └── skill-fiesta/     # Skill experimental

deploy.sh           # Script de deploy multi-hostname
.gitignore           # Exclusiones del repo
```

## Deploy

### Primer deploy en un equipo

```bash
# 1. Clonar o rsync el repo
git clone <url> ~/skills
# o via rsync desde cachy-gla:
rsync -avz --delete cachy-gla:skills/ ~/skills/

# 2. Ejecutar deploy (detecta hostname automáticamente)
cd ~/skills && bash deploy.sh

# 3. Configurar trust de symlinks (una sola vez)
# Agregar en ~/.openclaw/openclaw.json:
#   "skills": { "load": { "allowSymlinkTargets": ["~/skills"] } }

# 4. Restart gateway
systemctl --user restart openclaw-gateway

# 5. Verificar
openclaw doctor
```

### Actualizar skills

```bash
cd ~/skills && git pull && bash deploy.sh
```

## Mantenimiento

| Skill | Categoría | Mantenedor |
|-------|-----------|------------|
| shared/* | Ambos | Arquitecto (cachy-gla) |
| cachy-gla/* | cachy-gla | Arquitecto |
| raspi/* | Raspi | Qwen (Raspi) |

## Restore (ante fallo de implementación)

```bash
# Backup automático en ~/backups/
tar -xzf ~/backups/skills-backup-*.tar.gz -C ~/.openclaw/workspace/

# O usando el script:
~/backups/restore-skills.sh ~/backups/skills-backup-YYYYMMDD-HHMMSS.tar.gz
```

## Consideraciones multi-ambiente

Cada SKILL.md en shared/ incluye una sección `## Environment` que detalla:
- Qué hostname ejecuta cada parte del skill
- Dependencias específicas de cada equipo
- Endpoints, tokens y rutas locales

Verificar `uname -n` antes de ejecutar scripts específicos de plataforma.

## Matriz de Agent Cards

| Nodo | Skills en Agent Card |
|------|---------------------|
| cachy-gla | 12 (shared + cachy-gla) |
| Raspi | 16 (shared + raspi + built-ins) |
