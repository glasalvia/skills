#!/bin/bash
# linkedin_whatsapp_notify.sh - Envia digest de ofertas LinkedIn por WhatsApp
SKILL_DIR="$HOME/.openclaw/workspace/skills/linkedin-job-pipeline"
DIGEST_FILE="/tmp/linkedin_digest_whatsapp.txt"

cd "$SKILL_DIR" || exit 1
python3 linkedin_digest_export.py 2>/dev/null > "$DIGEST_FILE"

if [ -s "$DIGEST_FILE" ]; then
    /usr/local/bin/openclaw message send \
        --channel whatsapp \
        --target +5491164396711 \
        -m "$(cat "$DIGEST_FILE")" 2>/dev/null
    echo "$(date) Digest enviado OK" >> /tmp/linkedin_notify.log
else
    echo "$(date) Sin ofertas nuevas para notificar" >> /tmp/linkedin_notify.log
fi
