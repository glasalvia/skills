#!/usr/bin/env bash
# qwen-ctl.sh — Control del servidor local llama.cpp/Qwen3.6-35B-A3B
#
# Uso: qwen-ctl.sh <comando> [opciones]
#   status | start | stop | restart | logs | probe | doctor
#   task --title T --notes-file F [--agent A] [--board B]
#   dispatch --card ID [--board B]
#   verify --card ID
#   selftest
#
# Códigos de salida:
#   0 listo / éxito          1 detenido / fallo          2 cargando / puerto ajeno

set -uo pipefail
export LC_ALL=C

UNIT="${QWEN_UNIT:-llama-qwen.service}"
PORT="${QWEN_PORT:-8080}"
ALIAS="${QWEN_MODEL_ALIAS:-qwen3.6-35b-a3b}"
BASE="http://127.0.0.1:${PORT}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen-local"
LOCK_FILE="$STATE_DIR/inference.lock"
METRICS_FILE="$STATE_DIR/metrics.csv"
READY_TIMEOUT="${QWEN_READY_TIMEOUT:-180}"
OPENCLAW_CONFIG="${OPENCLAW_CONFIG:-$HOME/.openclaw/openclaw.json}"

mkdir -p "$STATE_DIR"

JSON=0
log()  { printf '%s\n' "$*" >&2; }
ok()   { printf 'OK    %s\n' "$*"; }
warn() { printf 'WARN  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; }
die()  { log "ERROR: $*"; exit 1; }

base() { printf '%s' "$BASE"; }

model_id() {
  curl -sf -m 3 "$BASE/v1/models" 2>/dev/null \
    | jq -r '.data[0].id // empty' 2>/dev/null || true
}

is_active() { systemctl --user is-active --quiet "$UNIT" 2>/dev/null; }

port_open() { ss -ltnH "sport = :$PORT" 2>/dev/null | grep -q .; }

in_flight() { ss -tnH state established "( sport = :$PORT )" 2>/dev/null | grep -q .; }

ready() { [ "$(model_id)" = "$ALIAS" ]; }

wait_ready() {
  local deadline=$(( $(date +%s) + READY_TIMEOUT ))
  while [ "$(date +%s)" -lt "$deadline" ]; do
    ready && return 0
    sleep 2
  done
  return 1
}

stray_pids() {
  local pid cg
  for pid in $(pgrep -f 'llama-server' 2>/dev/null || true); do
    [ "$pid" = "$$" ] && continue
    cg="$(cat "/proc/$pid/cgroup" 2>/dev/null || true)"
    case "$cg" in
      *"$UNIT"*) ;;
      *) printf '%s\n' "$pid" ;;
    esac
  done
}

vram_used() {
  nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null \
    | head -1 | tr -d ' '
}

acquire_lock() {
  exec 9>"$LOCK_FILE" || die "no se pudo abrir el lock $LOCK_FILE"
  if ! flock -n 9; then
    local holder; holder="$(cat "$LOCK_FILE" 2>/dev/null || true)"
    die "otra operación de inferencia está en curso (${holder:-lock ocupado})"
  fi
  printf 'pid=%s since=%s\n' "$$" "$(date -Is)" > "$LOCK_FILE"
}

release_lock() { : > "$LOCK_FILE" 2>/dev/null || true; }

# ---------------------------------------------------------------- status
cmd_status() {
  local st rc
  if ready; then st=ready; rc=0
  elif is_active; then st=loading; rc=2
  elif port_open; then st=foreign; rc=2
  else st=stopped; rc=1
  fi

  if [ "$JSON" = 1 ]; then
    jq -n --arg status "$st" --arg unit "$UNIT" --arg model "$(model_id)" \
          --argjson port "$PORT" --argjson exit "$rc" \
      '{status:$status,unit:$unit,model:$model,port:$port,exit:$exit}'
  else
    printf 'estado: %s · unidad: %s · puerto: %s · alias: %s\n' "$st" "$UNIT" "$PORT" "$ALIAS"
    [ "$st" = "foreign" ] && warn "el puerto $PORT lo ocupa un proceso fuera de $UNIT"
  fi
  return "$rc"
}

# ---------------------------------------------------------------- start
cmd_start() {
  local force=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --force) force=1 ;;
      *) die "opción desconocida: $1" ;;
    esac
    shift
  done

  if ready; then log "ya está listo"; return 0; fi

  local strays; strays="$(stray_pids)"
  if [ -n "$strays" ] && ! is_active; then
    fail "hay llama-server huérfano(s) fuera de la unidad: $strays"
    log "detenelos antes de arrancar, o el puerto quedará en disputa"
    return 1
  fi

  if ! is_active; then
    local used; used="$(vram_used)"
    if [ -n "$used" ] && [ "$used" -gt 2048 ] && [ "$force" != 1 ]; then
      fail "VRAM en uso: ${used} MiB. Se esperan ~10.5 GiB libres para cargar el modelo"
      log "si el uso es legítimo y esperás que el modelo entre igual, usá --force"
      return 1
    fi
    log "iniciando $UNIT…"
    systemctl --user start "$UNIT" || { fail "systemctl start falló"; return 1; }
  else
    log "$UNIT activo; esperando readiness…"
  fi

  if wait_ready; then
    ok "listo · $ALIAS · ${PORT}/v1"
    return 0
  fi

  fail "no alcanzó readiness en ${READY_TIMEOUT}s"
  journalctl --user -u "$UNIT" -n 20 --no-pager 2>/dev/null | tail -20
  return 1
}

# ---------------------------------------------------------------- stop
cmd_stop() {
  if ! is_active && ! port_open; then log "ya está detenido"; return 0; fi

  systemctl --user stop "$UNIT" || { fail "systemctl stop falló"; return 1; }

  local deadline=$(( $(date +%s) + 30 ))
  while [ "$(date +%s)" -lt "$deadline" ]; do
    if ! port_open && ! is_active; then
      ok "detenido; puerto $PORT libre"
      return 0
    fi
    sleep 1
  done

  fail "el servicio no terminó de liberar el puerto $PORT"
  return 1
}

# ---------------------------------------------------------------- restart
cmd_restart() {
  local force=0
  [ "${1:-}" = "--force" ] && force=1

  if in_flight && [ "$force" != 1 ]; then
    fail "hay inferencia en vuelo contra el puerto $PORT; reiniciar mataría el trabajo"
    log "esperá a que termine o usá --force"
    return 1
  fi

  cmd_stop || return 1
  cmd_start ${force:+--force}
}

# ---------------------------------------------------------------- logs
cmd_logs() {
  local follow=0 since="" lines=100
  while [ $# -gt 0 ]; do
    case "$1" in
      -f|--follow) follow=1 ;;
      --since) since="${2:-}"; shift ;;
      -n|--lines) lines="${2:-100}"; shift ;;
      *) die "opción desconocida: $1" ;;
    esac
    shift
  done

  local args=(-u "$UNIT" -n "$lines" --no-pager)
  [ -n "$since" ] && args+=(--since "$since")
  [ "$follow" = 1 ] && args+=(-f)

  journalctl --user "${args[@]}"
}

# ---------------------------------------------------------------- probe
cmd_probe() {
  ready || { fail "el servicio no está listo; corré start primero"; return 1; }

  local payload response
  payload="$(jq -n --arg m "$ALIAS" '{model:$m,messages:[{role:"user",content:"Responde solo: OK"}],temperature:0,max_tokens:24,chat_template_kwargs:{enable_thinking:false}}')"
  response="$(curl -sf -m 120 "$BASE/v1/chat/completions" -H 'Content-Type: application/json' -d "$payload")" \
    || { fail "la petición de prueba falló"; return 1; }

  local content pt prefill gen
  content="$(jq -r '.choices[0].message.content // ""' <<<"$response")"
  pt="$(jq -r '.usage.prompt_tokens // 0' <<<"$response")"
  prefill="$(jq -r '.timings.prompt_per_second // 0' <<<"$response")"
  gen="$(jq -r '.timings.predicted_per_second // 0' <<<"$response")"

  [ -n "$content" ] || { fail "respuesta vacía (posible thinking consumiendo max_tokens)"; return 1; }

  if [ ! -f "$METRICS_FILE" ]; then
    printf 'timestamp,model,prompt_tokens,prefill_tps,decode_tps\n' > "$METRICS_FILE"
  fi
  LC_ALL=C printf '%s,%s,%s,%.1f,%.1f\n' "$(date -Is)" "$ALIAS" "$pt" "$prefill" "$gen" >> "$METRICS_FILE"

  local pf gn
  pf="$(LC_ALL=C awk -v v="$prefill" 'BEGIN{printf "%.1f", v}')"
  gn="$(LC_ALL=C awk -v v="$gen" 'BEGIN{printf "%.1f", v}')"

  printf 'modelo      %s\n' "$ALIAS"
  printf 'prefill     %s tok/s (%s tokens)\n' "$pf" "$pt"
  printf 'decode      %s tok/s\n' "$gn"
  printf 'nota        prompt corto: mide arranque, no prefill sostenido\n'
  printf 'respuesta   %s\n' "$content"
  return 0
}

# ---------------------------------------------------------------- doctor
cmd_doctor() {
  local critical=0

  if systemctl --user cat "$UNIT" >/dev/null 2>&1; then
    ok "unidad $UNIT presente"
  else
    fail "unidad $UNIT ausente (ver assets/llama-qwen.service)"
    critical=1
  fi

  if systemctl --user is-enabled --quiet "$UNIT" 2>/dev/null; then
    ok "unidad habilitada al boot"
  else
    warn "unidad deshabilitada: no arranca sola tras reiniciar"
  fi

  if is_active; then ok "unidad activa"; else fail "unidad inactiva"; fi

  if [ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null || echo no)" = "yes" ]; then
    ok "linger activo: sobrevive al logout"
  else
    warn "linger desactivado: el servicio muere al cerrar sesión"
  fi

  local id; id="$(model_id)"
  if [ "$id" = "$ALIAS" ]; then
    ok "alias coincide: $id"
  elif [ -z "$id" ]; then
    fail "sin respuesta en $BASE/v1/models"
    critical=1
  else
    fail "alias distinto: servidor publica '$id', se espera '$ALIAS'"
    critical=1
  fi

  local strays; strays="$(stray_pids)"
  if [ -n "$strays" ]; then
    fail "llama-server huérfano(s): $strays"
    critical=1
  else
    ok "sin procesos huérfanos"
  fi

  if ! is_active && port_open; then
    fail "puerto $PORT ocupado por un proceso ajeno a la unidad"
    critical=1
  fi

  local used total
  used="$(vram_used)"; total="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')"
  [ -n "$used" ] && ok "VRAM ${used}/${total} MiB"
  local memavail; memavail="$(awk '/MemAvailable/ {printf "%d", $2/1024}' /proc/meminfo)"
  if [ "${memavail:-0}" -lt 2048 ]; then
    warn "RAM disponible baja: ${memavail} MiB (riesgo de eviction silenciosa)"
  else
    ok "RAM disponible ${memavail} MiB"
  fi

  if [ -f "$OPENCLAW_CONFIG" ]; then
    local reg
    reg="$(python3 - "$OPENCLAW_CONFIG" <<'PY'
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    p=d.get("models",{}).get("providers",{}).get("local-qwen",{})
    ids=[m.get("id") for m in p.get("models",[]) if isinstance(m,dict)]
    print(p.get("baseUrl","")+"|"+",".join(x for x in ids if x))
except Exception:
    print("|")
PY
)"
    case "$reg" in
      "$BASE/v1|$ALIAS") ok "proveedor local-qwen registrado y alineado" ;;
      *) fail "proveedor local-qwen desalineado: $reg"; critical=1 ;;
    esac
  else
    warn "no se encontró $OPENCLAW_CONFIG"
  fi

  # Deriva de flags en la unidad
  local exec_line
  exec_line="$(systemctl --user cat "$UNIT" 2>/dev/null | awk '/^ExecStart=/{print; exit}')"
  for flag in "--jinja" "--parallel 1" "-fa on"; do
    case "$exec_line" in
      *"$flag"*) ok "flag presente: $flag" ;;
      *) warn "flag ausente en ExecStart: $flag" ;;
    esac
  done

  if [ "$critical" = 1 ]; then
    fail "hay fallos críticos"
    return 1
  fi
  ok "sin fallos críticos"
  return 0
}

# ---------------------------------------------------------------- dispatch
card_status() {
  openclaw workboard show "$1" --json 2>/dev/null | jq -r '.card.status // empty'
}

cmd_dispatch() {
  local card="" board="default" timeout=900 no_start=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --card) card="${2:-}"; shift ;;
      --board) board="${2:-default}"; shift ;;
      --timeout) timeout="${2:-900}"; shift ;;
      --no-start) no_start=1 ;;
      *) die "opción desconocida: $1" ;;
    esac
    shift
  done
  [ -n "$card" ] || die "falta --card <id>"

  if ! ready; then
    if [ "$no_start" = 1 ]; then die "servicio no listo y --no-start fue indicado"; fi
    log "servicio no listo; iniciando…"
    cmd_start || die "no se pudo iniciar el servicio"
  fi

  acquire_lock
  trap release_lock EXIT

  local out
  out="$(openclaw workboard dispatch --board "$board" --admin --max-starts 1 --json 2>&1)" || {
    printf '%s\n' "$out" >&2; die "dispatch falló"; }

  if [ "$(jq -r '.startFailures | length' <<<"$out" 2>/dev/null || echo 0)" != "0" ]; then
    printf '%s\n' "$out" | jq '.startFailures'
    die "el worker no pudo iniciarse"
  fi

  local started_card
  started_card="$(jq -r '.started[0].cardId // empty' <<<"$out")"
  if [ -z "$started_card" ]; then
    die "no se inició ningún worker (¿tarjeta en ready?)"
  fi
  [ "$started_card" = "$card" ] || warn "se despachó $started_card, no $card"

  log "worker iniciado para $started_card; esperando cierre…"
  local deadline=$(( $(date +%s) + timeout ))
  local st=""
  while [ "$(date +%s)" -lt "$deadline" ]; do
    st="$(card_status "$card")"
    case "$st" in done|blocked|review) break ;; esac
    sleep 5
  done

  case "$st" in
    done) ok "tarjeta $card completada" ;;
    blocked) fail "tarjeta $card bloqueada"; return 1 ;;
    review) warn "tarjeta $card en revisión"; return 0 ;;
    *) fail "timeout: estado '$st'"; return 1 ;;
  esac

  openclaw workboard show "$card" --json 2>/dev/null \
    | jq -r '"resumen: " + (.card.metadata.automation.summary // "(sin resumen)") + "\nartefactos:\n" + ((.card.metadata.artifacts // []) | map("  " + .path) | join("\n"))'
}

# ---------------------------------------------------------------- task
cmd_task() {
  local title="" notes_file="" agent="el-merovingio" board="default" priority="normal"
  while [ $# -gt 0 ]; do
    case "$1" in
      --title) title="${2:-}"; shift ;;
      --notes-file) notes_file="${2:-}"; shift ;;
      --agent) agent="${2:-el-merovingio}"; shift ;;
      --board) board="${2:-default}"; shift ;;
      --priority) priority="${2:-normal}"; shift ;;
      *) die "opción desconocida: $1" ;;
    esac
    shift
  done
  [ -n "$title" ] || die "falta --title"
  [ -n "$notes_file" ] && [ -f "$notes_file" ] || die "falta --notes-file válido"

  local out card
  out="$(openclaw workboard create "$title" --agent "$agent" --board "$board" \
        --priority "$priority" --status ready --labels "qwen-local,merovingio" \
        --notes "$(cat "$notes_file")" --json 2>&1)" || { printf '%s\n' "$out" >&2; die "no se pudo crear la tarjeta"; }

  card="$(jq -r '.card.id // .id // empty' <<<"$out")"
  [ -n "$card" ] || die "respuesta de creación sin id: $out"
  ok "tarjeta $card creada en ready"

  cmd_dispatch --card "$card" --board "$board"
}

# ---------------------------------------------------------------- verify
cmd_verify() {
  local card=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --card) card="${2:-}"; shift ;;
      *) die "opción desconocida: $1" ;;
    esac
    shift
  done
  [ -n "$card" ] || die "falta --card <id>"

  local card_json; card_json="$(openclaw workboard show "$card" --json 2>/dev/null)" || die "no se pudo leer la tarjeta"
  local status; status="$(jq -r '.card.status' <<<"$card_json")"
  local failures=0

  printf 'tarjeta  %s\nestado   %s\n' "$card" "$status"

  local artifacts; artifacts="$(jq -r '(.card.metadata.artifacts // [])[] | .path' <<<"$card_json")"
  if [ -z "$artifacts" ]; then
    fail "sin artefactos declarados: nada que verificar"
    return 1
  fi

  local path
  while IFS= read -r path; do
    [ -f "$path" ] || { fail "artefacto ausente: $path"; failures=$((failures+1)); continue; }

    local jstatus jev
    jstatus="$(jq -r '.status // empty' "$path" 2>/dev/null)"
    jev="$(jq -r '.evidence | length' "$path" 2>/dev/null || echo 0)"

    if [ -z "$jstatus" ] || [ "${jev:-0}" = "0" ]; then
      fail "$path: contrato incompleto (status/evidence)"
      failures=$((failures+1))
      continue
    fi
    ok "$path: contrato presente (status=$jstatus, evidence=$jev)"

    local i=0
    while [ "$i" -lt "$jev" ]; do
      local cmd expected actual
      cmd="$(jq -r ".evidence[$i].cmd // empty" "$path")"
      expected="$(jq -r ".evidence[$i].output // empty" "$path")"

      if printf '%s' "$cmd" | grep -qiE '(^|[;&|[:space:]])(rm|rmdir|shred|dd|mkfs|truncate|sudo|su|shutdown|reboot|chmod|chown)([[:space:]]|$)|systemctl[[:space:]]+(start|stop|restart|enable|disable)|curl|wget|git[[:space:]]+push'; then
        fail "evidence[$i] rechazada por peligrosa: $cmd"
        failures=$((failures+1)); i=$((i+1)); continue
      fi

      actual="$(bash -c "$cmd" 2>&1 | head -c 500)"
      if [ "$(printf '%s' "$actual" | sed -e 's/[[:space:]]*$//')" = "$(printf '%s' "$expected" | sed -e 's/[[:space:]]*$//')" ]; then
        ok "evidence[$i] reproduce: $cmd"
      else
        fail "evidence[$i] diverge: $cmd"
        printf '  esperado: %s\n  obtenido: %s\n' "$expected" "$actual"
        failures=$((failures+1))
      fi
      i=$((i+1))
    done
  done <<<"$artifacts"

  [ "$failures" -eq 0 ] && { ok "verificación completa"; return 0; }
  fail "$failures discrepancia(s)"
  return 1
}

# ---------------------------------------------------------------- selftest
cmd_selftest() {
  local rc=0
  printf '== status ==\n'; cmd_status || rc=1
  printf '\n== probe ==\n';  cmd_probe  || rc=1
  printf '\n== doctor ==\n'; cmd_doctor || rc=1
  printf '\n'
  [ "$rc" -eq 0 ] && ok "selftest completo" || fail "selftest con fallos"
  return "$rc"
}

usage() {
  sed -n '3,14p' "$0" | sed 's/^# \{0,1\}//'
}

main() {
  local cmd="${1:-status}"; shift || true

  # --json global, aceptado después del comando
  local args=()
  for a in "$@"; do
    if [ "$a" = "--json" ]; then JSON=1; else args+=("$a"); fi
  done
  set -- ${args[@]+"${args[@]}"}

  case "$cmd" in
    status)   cmd_status ;;
    start)    cmd_start "$@" ;;
    stop)     cmd_stop ;;
    restart)  cmd_restart "$@" ;;
    logs)     cmd_logs "$@" ;;
    probe)    cmd_probe ;;
    doctor)   cmd_doctor ;;
    task)     cmd_task "$@" ;;
    dispatch) cmd_dispatch "$@" ;;
    verify)   cmd_verify "$@" ;;
    selftest) cmd_selftest ;;
    -h|--help|help) usage ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"
