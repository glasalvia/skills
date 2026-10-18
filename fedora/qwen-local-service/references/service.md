# Servicio llama.cpp local — unidad, flags y perfiles

## Unidad de referencia

`~/.config/systemd/user/llama-qwen.service` (usuario, no sistema).

```ini
[Unit]
Description=llama.cpp server — Qwen3.6-35B-A3B (local, OpenAI-compatible)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/glasalvia/opt/llama.cpp
Environment=LD_LIBRARY_PATH=/home/glasalvia/opt/llama.cpp/cudart-llama-b11711-bin-ubuntu-cuda-13.4-x64:/home/glasalvia/opt/llama.cpp/llama-b11711
ExecStart=/home/glasalvia/opt/llama.cpp/llama-b11711/llama-server \
  -m /home/glasalvia/models/qwen3.6-35b-a3b/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf \
  --alias qwen3.6-35b-a3b -ngl 999 --n-cpu-moe 28 -fa on --jinja \
  -c 131072 -ctk q8_0 -ctv q8_0 -b 1024 -ub 256 --parallel 1 \
  --host 127.0.0.1 --port 8080
Restart=on-failure
RestartSec=10
TimeoutStartSec=300

[Install]
WantedBy=default.target
```

## Por qué cada flag

| Flag | Razón |
|---|---|
| `-ngl 999` | todas las capas a GPU; los expertos MoE se excluyen con el flag siguiente |
| `--n-cpu-moe 28` | 28 capas de expertos en CPU: los pesos no entran en 12 GB de VRAM |
| `-fa on` | flash attention; reduce el costo del KV en contexto largo |
| `--jinja` | plantilla real del modelo; imprescindible para tool calling y `enable_thinking` |
| `-c 131072` | 128k de contexto; por encima de los 100k útiles |
| `-ctk/-ctv q8_0` | KV cuantizado; sin esto el contexto largo no entra |
| `-b 1024 -ub 256` | batching; el prefill sostenido medido lo aprovecha |
| `--parallel 1` | una ranura; más ranuras dividen el contexto y multiplican el KV |

## Política de arranque

Estado actual: `Linger=yes` + unidad `disabled`. El servicio sobrevive al logout pero **no** arranca tras un reinicio.

- Si debe estar siempre disponible: `systemctl --user enable llama-qwen.service`.
- Si debe arrancar solo cuando se lo pide: dejar `disabled` y usar `qwen-ctl.sh start` (o `task`/`dispatch`, que arrancan si hace falta).

## Perfiles de contexto por drop-in

No se edita la unidad principal. Se crea un drop-in:

```bash
mkdir -p ~/.config/systemd/user/llama-qwen.service.d
cat > ~/.config/systemd/user/llama-qwen.service.d/context-32k.conf <<'EOF'
[Service]
ExecStart=
ExecStart=/home/glasalvia/opt/llama.cpp/llama-b11711/llama-server \
  -m /home/glasalvia/models/qwen3.6-35b-a3b/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf \
  --alias qwen3.6-35b-a3b -ngl 999 --n-cpu-moe 20 -fa on --jinja \
  -c 32768 -ctk q8_0 -ctv q8_0 -b 1024 -ub 256 --parallel 1 \
  --host 127.0.0.1 --port 8080
EOF
systemctl --user daemon-reload
```

Bajar `--n-cpu-moe` de 28 a 20 sólo tiene sentido si el KV liberado deja lugar en VRAM; verificarlo con `doctor` y medir con `probe` antes y después. Un perfil no se adopta por intuición: se adopta por número.

## Registro en OpenClaw

`models.providers.local-qwen` con `baseUrl: http://127.0.0.1:8080/v1`, `api: openai-completions` y el modelo `qwen3.6-35b-a3b` con `compat.toolSchemaProfile: llamacpp`. El `id` del modelo debe coincidir **exactamente** con `--alias`; sin eso el discovery no reconcilia.
