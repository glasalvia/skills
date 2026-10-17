---
name: "raspberry-bridge"
description: "Conexión SSH a Raspberry Pi y transferencia de conocimiento/skills/código al agente vecino en la red local. Incluye gestión del nodo OpenClaw remoto."
---

# raspberry-bridge — Skill

## Descripción
Permite conectarse por SSH a la Raspberry Pi (192.168.1.65) para ejecutar comandos, transferir archivos, compartir skills con el otro agente OpenClaw que corre allí, y administrar el nodo remoto (actualización, servicios, diagnóstico de conexión).

## Prerrequisitos
- `sshpass` instalado en el sistema (`which sshpass` — disponible en cachy-gla)
- Credenciales del Raspi (ver sección Credenciales)

## Credenciales
- **Host:** `192.168.1.65`
- **Usuario:** `glasalvia`
- **Password keyring:** `***` (no rotar)

## Comandos de Ejecución Remota

### Ejecutar comando simple:
```bash
sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 '<comando>'
```

### Transferir archivo al Raspberry (desde este gateway):
```bash
# SCP directo con sshpass
sshpass -p "***" scp -o StrictHostKeyChecking=no <archivo_local> glasalvia@192.168.1.65:<ruta_destino>
```

La contraseña se pasa inline vía `sshpass -p`. No requiere archivos temporales ni wrappers Python.

### Copiar directorio completo (skill completa):
```bash
# 1. Empaquetar skill localmente
tar czf /tmp/skill.tar.gz -C <path_skill> .

# 2. SCP al raspberry
sshpass -p "***" scp -o StrictHostKeyChecking=no /tmp/skill.tar.gz glasalvia@192.168.1.65:/home/glasalvia/.openclaw/workspace/skills/

# 3. Desempaquetar en el raspberry
sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 'cd ~/.openclaw/workspace/skills && tar xzf skill.tar.gz && rm skill.tar.gz'

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
sshpass -p "***" scp -o StrictHostKeyChecking=no <archivo> glasalvia@192.168.1.65:<ruta_destino>
```

### Opción C: Ejecutar comando remoto
```bash
sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 '<comando>'
```

## Verificación Post-Transferencia
Después de transferir, verificar que el archivo llegó:
```bash
sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 'ls -la ~/.openclaw/workspace/skills/<nombre-skill>/'
```

## Notas de Seguridad
- La contraseña `***` es del keyring y **no debe rotarse**.
- `StrictHostKeyChecking=no` evita prompts interactivos de fingerprint.
- No almacenar credenciales en logs ni en el historial de chat.
- El método sshpass es directo, no requiere `/tmp/ssh_env` ni pexpect.

## Integración con OpenClaw
- El otro agente en la Raspberry tiene su propio workspace en `/home/glasalvia/.openclaw/workspace/`
- Las skills se colocan en `~/.openclaw/workspace/skills/<nombre>/SKILL.md`
- El gateway de la Raspberry puede recargar skills sin reinicio si está configurado para hot-reload

## Diagnóstico de conectividad
```bash
# Verificar que el Raspi responde
sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 'echo "OK"; uptime'

# Verificar que SCP funciona
echo "test" | sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 'cat > /tmp/ssh_test && echo OK'
```

## Gestión del Nodo OpenClaw en Raspi

### Actualizar OpenClaw vía SSH

El comando `openclaw update --yes` puede atascarse en la fase `updater-runtime-retention` en la Raspi (arm64, recursos limitados). Workaround probado:

```bash
# 1. Instalar la versión específica vía npm (bypassea la validación lenta)
sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 '\
  npm install -g --allow-scripts=@google/genai,esbuild,koffi,protobufjs,openclaw openclaw@2026.9.8\
'

# 2. Verificar que la versión se actualizó
sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 'openclaw --version'

# 3. Reiniciar el gateway para que corra la nueva versión
sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 'openclaw restart --yes'
# Nota: el restart corta la SSH. Esperar 30s y reconectar para verificar.

# 4. Verificar post-reinicio
sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 '\
  openclaw --version && openclaw status 2>/dev/null | grep -E "Gateway self|Gateway service|Node service"\
'
```

### Reiniciar Servicios Gateway y Node

```bash
# Reiniciar solo el node service (no corta la SSH)
sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 'systemctl --user restart openclaw-node'

# Verificar estado
sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 'systemctl --user is-active openclaw-node'

# Verificar PIDs después de reinicio
sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 '\
  systemctl --user show openclaw-gateway -p MainPID && systemctl --user show openclaw-node -p MainPID\
'
```

### Diagnosticar por qué el nodo aparece "sin conexión" en el Control UI

Cuando el nodo Raspi aparece como "sin conexión" o "desajuste de versiones" en el dashboard del Control UI, las causas raíz más probables son:

1. **IP destino incorrecta en el systemd unit:** `~/.config/systemd/user/openclaw-node.service` contiene la línea `ExecStart=... node run --host <IP_GATEWAY>`. Verificar que `<IP_GATEWAY>` coincida con la IP actual del gateway padre (cachy-gla: `192.168.1.72`).

2. **Registro stale en el gateway padre:** El archivo `~/.openclaw/nodes/paired.json.migrated` en cachy-gla conserva la versión y `lastConnectedAtMs` de la última conexión. No se actualiza hasta que el node service reconecte exitosamente.

3. **Node service no reiniciado post-update:** Los procesos del node service usan el binario de la versión anterior hasta que se reinician explícitamente con `systemctl --user restart openclaw-node`.

```bash
# Diagnóstico completo del node service desde cachy-gla
sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 '\
  echo "=== Service unit ==="
  cat /home/glasalvia/.config/systemd/user/openclaw-node.service
  echo ""
  echo "=== Running version ==="
  openclaw --version
  echo ""
  echo "=== Service status ==="
  systemctl --user status openclaw-node -l --no-pager | head -12
  echo ""
  echo "=== Gateway self ==="
  openclaw status 2>/dev/null | grep "Gateway self"\
'
```

### Remediar IP incorrecta en el systemd unit

```bash
sshpass -p "***" ssh -o StrictHostKeyChecking=no glasalvia@192.168.1.65 '\
  sed -i "s/--host [0-9.]*/--host 192.168.1.72/" /home/glasalvia/.config/systemd/user/openclaw-node.service
  systemctl --user daemon-reload
  systemctl --user restart openclaw-node
  echo "IP corregida, servicio reiniciado"\
'
```

### Control UI: Vista de nodos
- Los nodos aparecen como tarjetas de **Dispositivos** en el dashboard del Control UI, no como una página "Nodes" independiente.
- El estado "sin conexión" y "desajuste de versiones" se actualiza automáticamente cuando el node service reconecta con el gateway padre.
- La versión mostrada es la del último `lastConnectedAtMs`, no la versión actualmente instalada en el nodo. Si se actualizó el nodo pero no reconectó, el dashboard muestra la versión vieja.

### Archivos de registro del nodo
- **Registro de nodos pares (gateway padre):** `~/.openclaw/nodes/paired.json.migrated`
- **Registro de dispositivos pares (gateway padre):** `~/.openclaw/devices/paired.json.migrated`
- **Service unit (node remoto):** `~/.config/systemd/user/openclaw-node.service`
- **Service unit (gateway remoto):** `~/.config/systemd/user/openclaw-gateway.service`
