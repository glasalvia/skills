---
name: "skill-fiesta"
description: "Activar ambiente festivo: apagar plafón y ejecutar luces disco."
---

# Skill: skill-fiesta

Activa una secuencia festiva unificada.

## Pasos del Procedimiento

1. **Apagar Plafón:**
   Envía el comando para apagar `light.plafon` en Home Assistant.

2. **Efecto Disco:**
   Ejecuta el script existente `/home/glasalvia/.openclaw/workspace/disco_lights.py` con una duración preestablecida de 20 segundos. Al finalizar el script, las luces definidas (Luz 1-5 y Lampara B) quedarán configuradas en color celeste.
