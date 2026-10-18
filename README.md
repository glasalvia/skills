# Skills Repository — OpenClaw Multi-Node Skill Sync

Repositorio centralizado de skills para los agentes OpenClaw en fedora y Raspberry Pi.

## Estructura

```
skills/
├── shared/          # Skills presentes en AMBOS equipos
│   ├── actualizar-pasos/   # Pasos diarios → Google Sheets
│   ├── audio-tts/          # TTS a Google Home y Alexa
│   ├── cam-entity/         # Snapshot de cámara Tapo vía HA
│   ├── dev-orchestrator/   # Orquestación de tareas de desarrollo
│   ├── gog-workspace/      # Google Workspace CLI
│   ├── ml-api/             # Artículos de MercadoLibre vía API
│   └── noticias-argentina/ # Monitoreo RSS de noticias
├── fedora/       # Skills exclusivos de fedora
│   ├── music-downloader/       # Descarga MP3 vía yt-dlp
│   ├── notiscreen-send/        # Turing Smart Screen
│   ├── qwen-local-service/     # Ciclo de vida del Qwen local + Workboard
│   ├── raspberry-bridge/       # SSH a Raspi (fallback)
│   ├── raspi-a2a-bridge/       # Comunicación A2A
│   └── spec-kit/               # Spec-Driven Development
└── raspi/           # Skills exclusivos de Raspberry Pi
    ├── raspi-a2a-client/   # Cliente A2A del Pi
    ├── raspi-servarr-core/ # Servicios *arr en el Pi
    └── skill-fiesta/       # Skill experimental

deploy.sh           # Script de deploy multi-hostname
.gitignore          # Exclusiones del repo
```

## Deploy

### Primer deploy en un equipo

```bash
# 1. Clonar o rsync el repo
git clone <url> ~/skills
# o via rsync desde fedora:
rsync -avz --delete fedora:skills/ ~/skills/

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
| shared/* | Ambos | Arquitecto (fedora) |
| fedora/* | fedora | Arquitecto |
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

| Nodo | Skills del repo | Composición |
|------|-----------------|-------------|
| fedora | 13 | 7 shared + 6 fedora |
| Raspi | 10 | 7 shared + 3 raspi |

Los built-ins de OpenClaw se suman a estos números y no se cuentan aquí.
