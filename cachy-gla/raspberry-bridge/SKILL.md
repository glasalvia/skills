---
name: "raspberry-bridge"
description: "Conexión SSH a Raspberry Pi y transferencia de conocimiento/skills/código al agente vecino en la red local."
---

# raspberry-bridge — Skill

## Descripción
Permite conectarse por SSH a la Raspberry Pi (192.168.1.65) y transferir archivos, conocimiento o skills al otro agente OpenClaw que corre allí.

## Prerrequisitos
- Entorno virtual con pexpect: `/tmp/ssh_env`
  - Si no existe: `python3 -m venv /tmp/ssh_env && source /tmp/ssh_env/bin/activate && pip install pexpect --quiet`
- Wrapper de conexión en `/tmp/ssh_env/bin/ssh_connect.py`:

```python
#!/usr/bin/env python3
import pexpect, sys

host = sys.argv[1]
user = sys.argv[2]
password = sys.argv[3]
command = sys.argv[4] if len(sys.argv) > 4 else "echo connected"

child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no {user}@{host} "{command}"', timeout=15)
idx = child.expect([pexpect.TIMEOUT, 'password:', pexpect.EOF])
if idx == 1:
    child.sendline(password)
    child.expect(pexpect.EOF, timeout=15)
print(child.before.decode() if hasattr(child, 'before') and child.before else "")
```

## Credenciales
- **Host:** `192.168.1.65`
- **Usuario:** `glasalvia`
- **Password keyring:** `Capicua1221` (no rotar)

## Comandos de Ejecución Remota

### Ejecutar comando simple:
```bash
/tmp/ssh_env/bin/python3 /tmp/ssh_env/bin/ssh_connect.py 192.168.1.65 glasalvia Capicua1221 'comando_a_ejecutar'
```

### Transferir archivo al Raspberry (desde este gateway):
1. Escribir el contenido en un path local temporal
2. Ejecutar: `scp <archivo_local> glasalvia@192.168.1.65:<destino>`

Ejemplo con el wrapper:
```bash
# Crear archivo temporal y scp
echo "contenido" > /tmp/temp_file.txt
/tmp/ssh_env/bin/python3 -c "
import pexpect, sys
child = pexpect.spawn('scp /tmp/temp_file.txt glasalvia@192.168.1.65:/home/glasalvia/.openclaw/workspace/skills/mi-skill/SKILL.md', timeout=15)
idx = child.expect([pexpect.TIMEOUT, 'password:', pexpect.EOF])
if idx == 1:
    child.sendline('Capicua1221')
    child.expect(pexpect.EOF, timeout=30)
print(child.before.decode() if hasattr(child, 'before') and child.before else '')
" && rm /tmp/temp_file.txt
```

### Copiar directorio completo (skill completa):
```bash
# Empaquetar skill localmente
tar czf /tmp/skill.tar.gz -C <path_skill> .
# SCP al raspberry
/tmp/ssh_env/bin/python3 -c "
import pexpect, sys
child = pexpect.spawn('scp /tmp/skill.tar.gz glasalvia@192.168.1.65:/home/glasalvia/.openclaw/workspace/skills/', timeout=30)
idx = child.expect([pexpect.TIMEOUT, 'password:', pexpect.EOF])
if idx == 1:
    child.sendline('Capicua1221')
    child.expect(pexpect.EOF, timeout=60)
print(child.before.decode() if hasattr(child, 'before') and child.before else '')
" && rm /tmp/skill.tar.gz

# Desempaquetar en el raspberry
/tmp/ssh_env/bin/python3 /tmp/ssh_env/bin/ssh_connect.py 192.168.1.65 glasalvia Capicua1221 'cd ~/.openclaw/workspace/skills && tar xzf skill.tar.gz && rm skill.tar.gz'
```

## Flujo de Transferencia de Conocimiento/Skill/Código

### Opción A: Skill completa (recomendada)
1. Crear la skill localmente con `skill_workshop` o escribir SKILL.md directamente
2. Empaquetar el directorio de la skill en un tar.gz temporal
3. SCP al raspberry en `/home/glasalvia/.openclaw/workspace/skills/`
4. Desempaquetar remotamente
5. El otro agente tendrá acceso inmediato a la skill

### Opción B: Archivo individual (config, script, dato)
1. Escribir el contenido en un archivo temporal local
2. SCP al destino deseado en el raspberry
3. Limpiar archivo temporal

### Opción C: Ejecutar comando de diagnóstico/verificación
```bash
/tmp/ssh_env/bin/python3 /tmp/ssh_env/bin/ssh_connect.py 192.168.1.65 glasalvia Capicua1221 'comando'
```

## Verificación Post-Transferencia
Después de transferir, verificar que el archivo llegó:
```bash
/tmp/ssh_env/bin/python3 /tmp/ssh_env/bin/ssh_connect.py 192.168.1.65 glasalvia Capicua1221 'ls -la ~/.openclaw/workspace/skills/<nombre-skill>/'
```

## Notas de Seguridad
- La contraseña `Capicua1221` es del keyring y **no debe rotarse**.
- El wrapper usa `StrictHostKeyChecking=no` para evitar prompts interactivos.
- Archivos temporales deben limpiarse después de la transferencia.
- No almacenar credenciales en logs ni en el historial de chat.

## Ejemplo Práctico: Compartir una skill al otro agente
```bash
# 1. Empaquetar skill local (ejemplo con una skill llamada "mi-skill")
tar czf /tmp/mi-skill.tar.gz -C ~/.openclaw/workspace/skills/mi-skill .

# 2. SCP + desempaquetar en raspberry
/tmp/ssh_env/bin/python3 -c "
import pexpect, sys
child = pexpect.spawn('scp /tmp/mi-skill.tar.gz glasalvia@192.168.1.65:/home/glasalvia/.openclaw/workspace/skills/', timeout=30)
idx = child.expect([pexpect.TIMEOUT, 'password:', pexpect.EOF])
if idx == 1:
    child.sendline('Capicua1221')
    child.expect(pexpect.EOF, timeout=60)
print(child.before.decode() if hasattr(child, 'before') and child.before else '')
" && rm /tmp/mi-skill.tar.gz

# 3. Verificar que llegó
/tmp/ssh_env/bin/python3 /tmp/ssh_env/bin/ssh_connect.py 192.168.1.65 glasalvia Capicua1221 'ls ~/.openclaw/workspace/skills/mi-skill/'
```

## Integración con OpenClaw
- El otro agente en la Raspberry tiene su propio workspace en `/home/glasalvia/.openclaw/workspace/`
- Las skills se colocan en `~/.openclaw/workspace/skills/<nombre>/SKILL.md`
- El gateway de la Raspberry puede recargar skills sin reinicio si está configurado para hot-reload
