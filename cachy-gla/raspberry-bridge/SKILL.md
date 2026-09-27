---
name: "raspberry-bridge"
description: "Conexión SSH a Raspberry Pi y transferencia de conocimiento/skills/código al agente vecino en la red local."
---

# raspberry-bridge — Skill

## Descripción
Permite conectarse por SSH a la Raspberry Pi (192.168.1.65) para ejecutar comandos, transferir archivos y compartir skills con el otro agente OpenClaw que corre allí.

## Prerrequisitos
- `sshpass` instalado en el sistema (`which sshpass` — disponible en cachy-gla)
- Credenciales del Raspi (ver sección Credenciales)

## Credenciales
- **Host:** `192.168.1.65`
- **Usuario:** `glasalvia`
- **Password keyring:** `Capicua1221` (no rotar)

## Comandos de Ejecución Remota

### Ejecutar comando simple:
```bash
sshpass -p "Capicua1221" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 '<comando>'
```

### Transferir archivo al Raspberry (desde este gateway):
```bash
# SCP directo con sshpass
sshpass -p "Capicua1221" scp -o StrictHostKeyChecking=no <archivo_local> glasalvia@192.168.1.65:<ruta_destino>
```

La contraseña se pasa inline vía `sshpass -p`. No requiere archivos temporales ni wrappers Python.

### Copiar directorio completo (skill completa):
```bash
# 1. Empaquetar skill localmente
tar czf /tmp/skill.tar.gz -C <path_skill> .

# 2. SCP al raspberry
sshpass -p "Capicua1221" scp -o StrictHostKeyChecking=no /tmp/skill.tar.gz glasalvia@192.168.1.65:/home/glasalvia/.openclaw/workspace/skills/

# 3. Desempaquetar en el raspberry
sshpass -p "Capicua1221" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 'cd ~/.openclaw/workspace/skills && tar xzf skill.tar.gz && rm skill.tar.gz'

# 4. Limpiar local
rm /tmp/skill.tar.gz
```

## Flujo de Transferencia de Conocimiento/Skill/Código

### Opción A: Skill completa (recomendada)
1. Crear la skill localmente con `skill_workshop` o escribir SKILL.md directamente
2. Empaquetar el directorio de la skill en un tar.gz temporal
3. SCP al raspberry en `/home/glasalvia/.openclaw/workspace/skills/`
4. Desempaquetar remotamente
5. Limpiar archivo temporal local
6. El otro agente tendrá acceso inmediato a la skill

### Opción B: Archivo individual (config, script, dato)
```bash
sshpass -p "Capicua1221" scp -o StrictHostKeyChecking=no <archivo> glasalvia@192.168.1.65:<ruta_destino>
```

### Opción C: Ejecutar comando remoto
```bash
sshpass -p "Capicua1221" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 '<comando>'
```

## Verificación Post-Transferencia
Después de transferir, verificar que el archivo llegó:
```bash
sshpass -p "Capicua1221" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 'ls -la ~/.openclaw/workspace/skills/<nombre-skill>/'
```

## Notas de Seguridad
- La contraseña `Capicua1221` es del keyring y **no debe rotarse**.
- `StrictHostKeyChecking=no` evita prompts interactivos de fingerprint.
- No almacenar credenciales en logs ni en el historial de chat.
- El método sshpass es directo, no requiere `/tmp/ssh_env` ni pexpect.

## Ejemplo Práctico: Compartir una skill al otro agente
```bash
# 1. Empaquetar skill local
tar czf /tmp/mi-skill.tar.gz -C ~/.openclaw/workspace/skills/mi-skill .

# 2. SCP al raspberry
sshpass -p "Capicua1221" scp -o StrictHostKeyChecking=no /tmp/mi-skill.tar.gz glasalvia@192.168.1.65:/home/glasalvia/.openclaw/workspace/skills/

# 3. Desempaquetar remotamente
sshpass -p "Capicua1221" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 'cd ~/.openclaw/workspace/skills && tar xzf skill.tar.gz && rm skill.tar.gz'

# 4. Verificar que llegó
sshpass -p "Capicua1221" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 'ls ~/.openclaw/workspace/skills/mi-skill/'

# 5. Limpiar local
rm /tmp/mi-skill.tar.gz
```

## Integración con OpenClaw
- El otro agente en la Raspberry tiene su propio workspace en `/home/glasalvia/.openclaw/workspace/`
- Las skills se colocan en `~/.openclaw/workspace/skills/<nombre>/SKILL.md`
- El gateway de la Raspberry puede recargar skills sin reinicio si está configurado para hot-reload

## Diagnóstico de conectividad
```bash
# Verificar que el Raspi responde
sshpass -p "Capicua1221" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 'echo "OK"; uptime'

# Verificar que SCP funciona
echo "test" | sshpass -p "Capicua1221" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 'cat > /tmp/ssh_test && echo OK'
```