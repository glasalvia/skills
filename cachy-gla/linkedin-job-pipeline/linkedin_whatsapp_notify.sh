#!/bin/bash
SKILL_DIR="$HOME/.openclaw/workspace/skills/linkedin-job-pipeline"
DIGEST_FILE="/tmp/linkedin_digest_whatsapp.txt"

cd "$SKILL_DIR" || exit 1
python3 linkedin_digest_export.py 2>/dev/null > "$DIGEST_FILE"

if [ -s "$DIGEST_FILE" ]; then
    /usr/local/bin/openclaw message send \
        --channel whatsapp \
        --target +5491164396711 \
        -m "$(cat "$DIGEST_FILE")" >/dev/null 2>&1
fi
