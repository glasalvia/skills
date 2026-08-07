---
name: "gog-workspace"
description: "Procedimientos operativos para gog CLI: autenticación OAuth, keyring, Gmail/Calendar/Drive/Contacts, diagnóstico y reconstrucción."
---

# gog CLI — Google Workspace desde terminal

## Propósito
Esta skill documenta el uso completo de `gog` (Google OAuth Gateway CLI) para interactuar con Gmail, Calendar, Drive y Contacts desde OpenClaw sin depender de la sesión gráfica del usuario.

## Configuración permanente

Las variables de entorno están en `openclaw.json` y se cargan al iniciar el gateway. El agente **no necesita exportarlas.**

```bash
openclaw config set env.vars.GOG_KEYRING_PASSWORD "Capicua1221"
openclaw config set env.vars.GOG_KEYRING_BACKEND file
openclaw config set env.vars.GOG_ACCOUNT raspilasalvia@gmail.com
# Requiere restart del gateway
```

**Archivos relevantes:**
- Binario: `/usr/bin/gog` v0.32.0
- Client secret: `~/.config/gog/client_secret.json`
- Keyring (encriptado AES-256-GCM): `~/.local/share/gogcli/keyring/`
- Config backend: `~/.config/gogcli/config.json` (contiene `keyring_backend: file`)

**Password del keyring:** `Capicua1221`. No rotar. Si cambia, los tokens se vuelven ilegibles.

## Arquitectura del keyring (4 entradas)

| Archivo | Propósito |
|---------|-----------|
| `_gogcli_key_v1_Y2xpZW50L2RlZmF1bHQvY2xpZW50LXNlY3JldA` | OAuth client_id + client_secret |
| `_gogcli_key_v1_dG9rZW46ZGVmYXVsdDpyYXNwaWxhc2FsdmlhQGdtYWlsLmNvbQ` | Refresh token (usado por gmail, calendar, drive, contacts) |
| `_gogcli_key_v1_dG9rZW46cmFzcGlsYXNhbHZpYUBnbWFpbC5jb20` | Refresh token (usado por auth doctor) |
| `_gogcli_key_v1_dG9rZW4tc3ViOmRlZmF1bHQ6MTE3MTI2NTU1MTYwMTgyNjMwOTgz` | Suscripción interna |

## Comandos de diagnóstico

```bash
gog auth status                          # Estado general
gog auth doctor                          # Diagnóstico completo (keyring, tokens, permisos)
gog auth list                            # Cuentas almacenadas
gog auth tokens export raspilasalvia@gmail.com --out /tmp/token.json --overwrite  # Exportar (contiene secretos)
gog auth credentials ~/.config/gog/client_secret.json                              # Almacenar credenciales OAuth
```

## Uso diario

### Gmail
```bash
gog gmail search 'is:unread' --max 20 --no-input
gog gmail search 'from:noreply@empresa.com newer_than:7d' --max 10 --no-input
gog gmail send --to a@b.com --subject "Asunto" --body "Mensaje"
gog gmail send --to a@b.com --subject "Asunto" --body-file ./mensaje.txt
```

### Calendar
```bash
gog calendar events primary --from 2026-07-04T00:00:00 --to 2026-07-04T23:59:59 --json
```

### Drive
```bash
gog drive search "query" --max 10 --no-input
```

### Contacts
```bash
gog contacts list --max 20 --no-input
```

## Errores comunes

### `Secret not found in keyring (refresh token missing)`

**Causas:**
1. Password del keyring incorrecta (se cambió `GOG_KEYRING_PASSWORD` respecto a cuando se autenticó)
2. Token corrupto por importación defectuosa (se pasó el JSON exportado en lugar del token crudo a `--refresh-token-file`)
3. Keyring backend no configurado como `file`

### `aes.KeyUnwrap(): integrity check failed`

Password incorrecta. La clave de encriptación no coincide con la usada al crear los tokens. Requiere reconstrucción desde cero.

## Reconstrucción desde cero (procedimiento canónico)

**Precondición:** `client_secret.json` válido en `~/.config/gog/`.

```bash
# 1. Limpiar tokens corruptos
export GOG_KEYRING_BACKEND=file
export GOG_KEYRING_PASSWORD="***"
export GOG_ACCOUNT="raspilasalvia@gmail.com"
gog auth remove raspilasalvia@gmail.com --force -y
rm -f ~/.local/share/gogcli/keyring/_gogcli_key_*

# 2. Configurar backend y credenciales
gog auth keyring file
gog auth credentials ~/.config/gog/client_secret.json

# 3. Flujo OAuth manual (sin TTY interactivo)
gog auth add raspilasalvia@gmail.com --services "gmail,calendar,drive,contacts" --manual --force-consent
# → El comando imprime una URL de autorización
# → Copiar la URL, abrir en navegador, autorizar con la cuenta Google
# → Google redirige a http://127.0.0.1:XXXXX/oauth2/callback?code=***&state=*** (la página no carga, es normal)
# → Copiar la URL COMPLETA de redirección y pegarla en el prompt "Paste redirect URL"
# → El flujo OAuth se completa y los tokens se almacenan en el keyring

# 4. Verificar
gog gmail search 'is:unread' --max 1 --no-input
```

**Nota sobre `--manual`:** Sin TTY interactivo, `gog auth add` no puede abrir navegador. El flag `--manual` imprime la URL de autorización para copiarla manualmente. El flag `--force-consent` fuerza la re-autorización incluso si ya hay consentimiento previo.

## Emergencia: access token directo (bypass keyring, expira ~1h)

```bash
gog --access-token="$(cat /tmp/access_token.txt)" gmail search 'is:unread' --max 10 --no-input
# O vía variable de entorno:
export GOG_ACCESS_TOKEN="***"
```

## Lecciones aprendidas

1. **Causa raíz del problema original (2026-07-04):** La importación original del refresh token usó una password que no coincidía con la de lectura, o se importó el JSON exportado en lugar del token crudo. `auth doctor` daba OK porque verificaba `token:raspilasalvia@gmail.com`, pero `gmail` buscaba `token:default:raspilasalvia@gmail.com` y esa entrada estaba corrupta.
2. **La password del keyring es el punto único de fallo.** Mientras no se rote, el sistema es estable. Si se rota, reconstrucción completa.
3. **`gog auth add` requiere `--manual --force-consent` en entornos sin TTY.** Sin estos flags, el comando falla o no puede completar el flujo OAuth.
4. **Las variables de entorno deben estar en `openclaw.json`**, no en el shell del usuario, porque el proceso del agente no hereda el entorno de zsh.

## Environment
- **cachy-gla:** Gog CLI instalado (`/usr/bin/gog` v0.32.0). Keyring con password `Capicua1221`. Variables de entorno en `openclaw.json`.
- **Raspi:** No disponible (sin gog CLI ni keyring configurados).
- **Hostname check:** Si `uname -n` contiene "raspi", informar que el skill no está disponible.
