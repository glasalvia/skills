---
name: "sdxl-image-generator"
description: "Generación de imágenes con SDXL optimizada para RTX 5070 12GB. Soporta Juggernaut XL, RealVisXL, Base y Turbo con prompt engineering automático."
---

# SDXL Image Generator — Skill de Generación de Imágenes

## Descripción

Skill para generar imágenes de máxima calidad usando Stable Diffusion XL en una NVIDIA RTX 5070 (12 GB VRAM, Blackwell sm_120). Soporta múltiples modelos y modos de calidad, con prompt engineering automático y pipeline optimizado para la GPU.

## Requisitos

- Entorno virtual con Python 3.12 en `/home/glasalvia/stable-diffusion/sd_env/`
- PyTorch nightly con CUDA 12.8 (soporte Blackwell sm_120)
- Dependencias: `diffusers`, `transformers`, `accelerate`
- Modelos en cache HuggingFace: `~/.cache/huggingface/hub/`
- **No usar `sudo`** — todas las dependencias se instalan con `uv pip` en el venv

## Arquitectura del Pipeline

```
┌─────────────────────────────────────────────────────────┐
│              SDXL IMAGE GENERATOR                        │
│                                                          │
│  1. RESOLVER MODELO                                      │
│     ├─ juggernaut (default): RunDiffusion/Juggernaut-XL │
│     ├─ realvis: SG161222/RealVisXL_V5.0                 │
│     ├─ base: stabilityai/stable-diffusion-xl-base-1.0   │
│     └─ turbo: stabilityai/sdxl-turbo                     │
│                                                          │
│  2. RESOLVER MODO                                        │
│     ├─ max (default): 30 steps, máxima calidad          │
│     ├─ quality: 30 steps, balance calidad/velocidad     │
│     └─ fast: 2-4 steps (solo Turbo)                     │
│                                                          │
│  3. ENRIQUECER PROMPT (modo raw=false)                  │
│     ├─ Quality boosters: masterpiece, 8K, sharp focus   │
│     ├─ Lighting: professional studio lighting           │
│     └─ Negative prompt curado por modelo                │
│                                                          │
│  4. CONFIGURAR SCHEDULER                                 │
│     └─ DPM++ 2M Karras (óptimo calidad/velocidad)      │
│                                                          │
│  5. GENERAR                                              │
│     ├─ 1024x1024 nativa SDXL                            │
│     ├─ guidance_scale variable por modelo               │
│     └─ VAE tiled + sliced (optimización VRAM)           │
│                                                          │
│  6. GUARDAR                                              │
│     └─ ~/stable-diffusion/output/<timestamp>_<slug>.png │
└─────────────────────────────────────────────────────────┘
```

## Modelos Soportados

| Modelo | Repo ID | Peso | Uso óptimo | Guidance |
|--------|-----|------|-----------|----------|
| `juggernaut` | RunDiffusion/Juggernaut-XL-v9 | ~10 GB | Fotorrealismo general (default) | 5.0 |
| `realvis` | SG161222/RealVisXL_V5.0 | ~10 GB | Retratos, piel, detalle facial | 4.0 |
| `base` | stabilityai/stable-diffusion-xl-base-1.0 | ~7 GB | Versátil, buena adherencia al prompt | 7.5 |
| `turbo` | stabilityai/sdxl-turbo | ~5 GB | Iteraciones rápidas (1-4 steps) | 0.0 |

### Nota sobre carga de modelos

Juggernaut XL v9 y RealVisXL V5.0 existen en formato Diffusers completo en HuggingFace Hub. Se usa `from_pretrained()` directamente con el `repo_id` — no se requiere `from_single_file()` ni descarga manual de safetensors. El cache de HuggingFace (`~/.cache/huggingface/hub/`) maneja la persistencia automáticamente.

## Parámetros del CLI

```bash
source ~/stable-diffusion/sd_env/bin/activate
python ~/stable-diffusion/generate.py "<prompt>" [opciones]
```

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `prompt` | (requerido) | Descripción de la imagen en español o inglés |
| `--model` | `juggernaut` | Modelo: `juggernaut`, `realvis`, `base`, `turbo` |
| `--mode` | `max` | Calidad: `max` (30 steps), `quality` (30 steps), `fast` (2-4 steps) |
| `--steps` | auto | Override de steps (auto = óptimo por modo) |
| `--seed` | random | Seed fijo para reproducibilidad |
| `--raw` | false | Deshabilita prompt engineering automático |
| `--negative` | auto | Negative prompt manual (anula el curado) |
| `--output` | auto | Ruta de salida (auto = timestamp + slug) |

## Modos de Calidad

### `fast` (solo modelo turbo)
- SDXL Turbo + Euler Ancestral
- 2 steps, guidance_scale=0.0
- ~0.5 segundos, VRAM pico ~7.7 GB
- Ideal para iterar rápido sobre ideas

### `quality`
- Juggernaut/RealVis/Base + DPM++ 2M Karras
- 30 steps con guidance por modelo
- ~7-8 segundos, VRAM pico ~9.8 GB (Juggernaut)
- Balance óptimo calidad/velocidad

### `max` (default)
- Igual que `quality` (30 steps, DPM++ 2M Karras)
- Reservado para futuro: hires.fix o upscaling cuando haya más VRAM
- Actualmente funcionalmente idéntico a `quality`

## Decisión sobre SDXL Refiner

El SDXL Refiner **no se incluye** en el pipeline. Motivos:

1. **Juggernaut XL v9 y RealVisXL V5.0 ya producen detalles de nivel profesional.** El Refiner fue diseñado para compensar carencias del SDXL Base original, pero los fine-tunes comunitarios ya corrigieron esas deficiencias en el entrenamiento.
2. **Costo sin beneficio:** Descargar ~5 GB adicionales, overhead de 4-8s por cambio de pipeline, y la diferencia visual es imperceptible con Juggernaut.
3. **Consenso de la comunidad:** La comunidad de Stable Diffusion (Reddit, CivitAI, Discord) abandonó el Refiner como práctica estándar en 2024-2025 para fine-tunes.

## Prompt Engineering (modo raw=false)

### Quality Boosters automáticos
Cada prompt del usuario recibe:
- **Prefijo de calidad:** `masterpiece, best quality,`
- **Sufijos según modelo:**
  - Juggernaut: `, professional photography, sharp focus, high detail, 8K`
  - RealVis: `, photorealistic, hyperdetailed skin texture, 8K, award-winning photo`
  - Base: `, 8K, sharp focus, professional lighting, highly detailed`
  - Turbo: `, high quality, sharp`

### Negative Prompts por modelo
- **Juggernaut:** `ugly, deformed, noisy, blurry, low contrast, text, watermark, signature, bad anatomy, bad hands, extra fingers, mutated hands, poorly drawn face, cloned face, disfigured, gross proportions, missing limbs, extra limbs, floating limbs, disconnected limbs, out of frame, cropped, worst quality, low quality, jpeg artifacts, grainy`
- **RealVis:** `(octane render, render, drawing, anime, bad photo, bad photography:1.3), (worst quality, low quality, blurry:1.2), (bad teeth, deformed teeth, deformed lips), (bad anatomy, bad proportions:1.1), (deformed iris, deformed pupils), (deformed eyes, bad eyes), (deformed face, ugly face, bad face), (deformed hands, bad hands, fused fingers), morbid, mutilated, mutation, disfigured`
- **Base:** `cartoon, painting, illustration, 3d render, low quality, blurry, deformed, ugly, bad anatomy, extra limbs, watermark, text, signature, cropped, jpeg artifacts`

## Optimizaciones de VRAM

1. **VAE tiled + sliced:** `pipe.vae.enable_tiling()` + `pipe.vae.enable_slicing()` — necesario para decodificar 1024x1024 sin OOM en 12 GB
2. **fp16 obligatorio:** `torch_dtype=torch.float16` en todos los pipelines
3. **`use_safetensors=True`** siempre (más rápido y seguro)
4. **`torch.cuda.empty_cache()`** después de cada generación

## Procedimiento de Uso

### Primera generación
```
Usuario: "generame una imagen de un gato siamés con camiseta de Argentina"
→ La skill usa modo 'max' con Juggernaut, enriquece el prompt, genera en ~8s
→ Guarda en ~/stable-diffusion/output/20260629_001234_gato_siames_argentina.png
```

### Iteración rápida
```
Usuario: "generame la misma imagen pero con un perro --mode fast --model turbo"
→ Usa Turbo a 2 steps, genera en ~0.5s
```

### Prompt avanzado (sin magia)
```
Usuario: "generame [prompt detallado] --raw --negative 'mis negativos' --steps 40"
→ Sin enriquecimiento automático, control total
```

## Métricas de Rendimiento (RTX 5070, medidas reales)

| Pipeline | Tiempo carga | Tiempo gen | VRAM pico | Calidad |
|----------|-------------|-----------|-----------|---------|
| Turbo fast | ~1s | ~0.5s | 7.7 GB | Baja |
| Base quality | ~2s | ~8s | 10 GB | Alta |
| Juggernaut quality | ~1.5s | ~7s | 9.8 GB | Muy alta |

## Script Principal

El script reside en `~/stable-diffusion/generate.py`. Es un CLI autocontenido que:
1. Resuelve qué pipeline usar según `--model` y `--mode`
2. Para modelos Diffusers (juggernaut, realvis, base, turbo): usa `from_pretrained()` con cache automática de HuggingFace
3. Enriquece el prompt si `--raw` no está seteado
4. Configura el scheduler DPM++ 2M Karras para modos `quality` y `max`
5. Ejecuta la generación con VAE optimizado (tiling + slicing)
6. Reporta: ruta de salida, tiempo, VRAM pico, seed usado

## Mantenimiento

- **Actualizar PyTorch a estable:** cuando PyTorch 2.12 llegue a release estable con soporte sm_120, migrar del nightly
- **Nuevos modelos:** agregar entrada en el diccionario `MODELS` del script con `repo_id` y config de prompt
- **Upscaling futuro:** si se adquiere una GPU con >16 GB VRAM, implementar hires.fix como extensión del modo `max`

## Troubleshooting

| Error | Causa probable | Solución |
|-------|---------------|----------|
| `CUDA error: no kernel image available` | PyTorch sin soporte sm_120 | Reinstalar PyTorch nightly cu128 |
| OOM en generación | VRAM insuficiente | Verificar que VAE tiling está activo |
| `AttributeError: 'CLIPTextModel' object has no attribute 'text_model'` | `from_single_file()` incompatible con transformers | Usar `from_pretrained()` con repo Diffusers |
| Imagen de baja calidad | Steps insuficientes o guidance incorrecto | Usar `--steps 40`, verificar guidance del modelo |
| Descarga lenta de modelo | HuggingFace Hub con throttling | Primera descarga de cada modelo es ~10-15 min; luego es instantáneo desde cache |
