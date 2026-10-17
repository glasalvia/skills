#!/usr/bin/env python3
"""
SDXL Image Generator — Skill de generación de imágenes de máxima calidad.
Pipeline optimizado para NVIDIA RTX 5070 (12 GB VRAM, Blackwell sm_120).

Uso:
    source ~/stable-diffusion/sd_env/bin/activate
    python generate.py "un gato siamés con camiseta de Argentina"
    python generate.py "prompt" --model juggernaut --mode max
    python generate.py "prompt" --model turbo --mode fast
    python generate.py "prompt" --raw --steps 50 --negative "mis negativos"
"""

import argparse
import os
import re
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore", message=".*sm_120.*")

import torch
from diffusers import (
    StableDiffusionXLPipeline,
    StableDiffusionXLImg2ImgPipeline,
    DPMSolverMultistepScheduler,
    EulerDiscreteScheduler,
)

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path.home() / "stable-diffusion" / "output"
MODELS_DIR = Path.home() / "stable-diffusion" / "models"

MODELS = {
    "juggernaut": {
        "type": "single_file",
        "file": "JuggernautXL_v9_RunDiffusionPhoto_v2.safetensors",
        "guidance_scale": 5.0,
        "quality_suffix": ", professional photography, sharp focus, high detail, 8K",
        "negative_prompt": (
            "ugly, deformed, noisy, blurry, low contrast, text, watermark, "
            "bad anatomy, bad hands, extra fingers, mutated hands, poorly drawn face, "
            "disfigured, missing limbs, extra limbs, out of frame, cropped, "
            "worst quality, low quality, jpeg artifacts, grainy"
        ),
    },
    "realvis": {
        "type": "single_file",
        "file": "RealVisXL_V5.0_fp16.safetensors",
        "guidance_scale": 4.0,
        "quality_suffix": ", photorealistic, hyperdetailed skin texture, 8K, award-winning photo",
        "negative_prompt": (
            "(octane render, render, drawing, anime, bad photo, bad photography:1.3), "
            "(worst quality, low quality, blurry:1.2), (bad teeth, deformed lips), "
            "(bad anatomy, bad proportions:1.1), (deformed iris, deformed pupils), "
            "(deformed eyes, bad eyes), (deformed face, ugly face, bad face), "
            "(deformed hands, bad hands, fused fingers), morbid, mutilated, mutation, disfigured"
        ),
    },
    "base": {
        "type": "diffusers",
        "repo_id": "stabilityai/stable-diffusion-xl-base-1.0",
        "guidance_scale": 7.5,
        "quality_suffix": ", 8K, sharp focus, professional lighting, highly detailed",
        "negative_prompt": (
            "cartoon, painting, illustration, 3d render, low quality, blurry, "
            "deformed, ugly, bad anatomy, extra limbs, watermark, text, cropped"
        ),
    },
    "turbo": {
        "type": "diffusers",
        "repo_id": "stabilityai/sdxl-turbo",
        "guidance_scale": 0.0,
        "quality_suffix": ", high quality, sharp",
        "negative_prompt": "",
    },
}

REFINER_ID = "stabilityai/stable-diffusion-xl-refiner-1.0"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def slugify(text: str, max_len: int = 50) -> str:
    """Convertir prompt a slug para nombre de archivo."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "_", slug)
    return slug[:max_len].strip("_")


def build_prompt(raw_prompt: str, model_cfg: dict, raw: bool) -> str:
    """Enriquecer el prompt con quality boosters del modelo."""
    if raw:
        return raw_prompt
    suffix = model_cfg.get("quality_suffix", "")
    return f"masterpiece, best quality, {raw_prompt}{suffix}"


def format_vram(gb: float) -> str:
    return f"{gb:.1f} GB"


# ---------------------------------------------------------------------------
# Carga de modelos
# ---------------------------------------------------------------------------


def load_base_pipeline(model_key: str):
    """Cargar el pipeline base según el modelo."""
    model_cfg = MODELS[model_key]
    print(f"Cargando {model_key}...", flush=True)

    if model_key == "turbo":
        pipe = StableDiffusionXLPipeline.from_pretrained(
            model_cfg["repo_id"],
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True,
        )
    elif model_cfg["type"] == "single_file":
        safetensor_path = MODELS_DIR / model_cfg["file"]
        if not safetensor_path.exists():
            print(f"\nERROR: {safetensor_path} no encontrado.", file=sys.stderr)
            from urllib.parse import quote
            print(f"Descargar con:", file=sys.stderr)
            print(f"  wget <URL> -O {safetensor_path}", file=sys.stderr)
            sys.exit(1)
        pipe = StableDiffusionXLPipeline.from_single_file(
            str(safetensor_path),
            torch_dtype=torch.float16,
            use_safetensors=True,
        )
    else:  # diffusers
        pipe = StableDiffusionXLPipeline.from_pretrained(
            model_cfg["repo_id"],
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True,
        )

    return pipe.to("cuda")


def load_refiner_pipeline():
    """Cargar el pipeline refiner."""
    print("Cargando refiner...", flush=True)
    pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
        REFINER_ID,
        torch_dtype=torch.float16,
        variant="fp16",
        use_safetensors=True,
    )
    return pipe.to("cuda")


def configure_scheduler(pipe, mode: str):
    """Configurar el scheduler óptimo según modo."""
    if mode == "fast":
        pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
    else:
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            pipe.scheduler.config,
            algorithm_type="dpmsolver++",
            solver_order=2,
            use_karras_sigmas=True,
        )


# ---------------------------------------------------------------------------
# Generación
# ---------------------------------------------------------------------------


def generate(args):
    t_start = time.time()
    model_cfg = MODELS[args.model]

    # --- Cargar base ---
    pipe_base = load_base_pipeline(args.model)

    # VAE optimizations for 12 GB VRAM
    pipe_base.vae.enable_tiling()
    pipe_base.vae.enable_slicing()

    configure_scheduler(pipe_base, args.mode)
    vram_loaded = torch.cuda.memory_allocated() / 1024**3
    print(f"Modelo cargado. VRAM usada: {format_vram(vram_loaded)}", flush=True)

    # --- Build prompt ---
    prompt = build_prompt(args.prompt, model_cfg, args.raw)
    negative = args.negative if args.negative else model_cfg.get("negative_prompt", "")
    guidance_scale = model_cfg["guidance_scale"]

    # --- Resolver steps ---
    if args.mode == "fast":
        steps_base = 2
        denoising_end = 1.0
    elif args.mode == "max":
        steps_base = 25
        denoising_end = 0.8
    else:  # quality
        steps_base = 30
        denoising_end = 1.0

    if args.steps:
        steps_base = args.steps
        denoising_end = 1.0 if args.mode != "max" else 0.8

    print(f"Prompt: {prompt}", flush=True)
    if negative:
        print(f"Negative: {negative}", flush=True)
    print(f"Mode: {args.mode} | Model: {args.model} | Steps: {steps_base} | Guidance: {guidance_scale}", flush=True)

    # --- Generate latents ---
    if args.mode == "max" and args.model != "turbo":
        # Base generates up to 80%, refiner finishes the rest
        latents = pipe_base(
            prompt=prompt,
            negative_prompt=negative,
            num_inference_steps=steps_base,
            denoising_end=0.8,
            guidance_scale=guidance_scale,
            output_type="latent",
        ).images

        # Free base model
        del pipe_base
        torch.cuda.empty_cache()

        # Load refiner
        pipe_refiner = load_refiner_pipeline()
        pipe_refiner.vae.enable_tiling()
        pipe_refiner.vae.enable_slicing()

        refiner_steps = 8
        if args.steps and args.mode == "max":
            refiner_steps = max(4, int(args.steps * 0.2))

        image = pipe_refiner(
            prompt=prompt,
            negative_prompt=negative,
            image=latents,
            num_inference_steps=refiner_steps,
            denoising_start=0.8,
            guidance_scale=guidance_scale,
        ).images[0]

        del pipe_refiner
    else:
        image = pipe_base(
            prompt=prompt,
            negative_prompt=negative,
            num_inference_steps=steps_base,
            guidance_scale=guidance_scale,
        ).images[0]

        del pipe_base

    torch.cuda.empty_cache()

    # --- Save ---
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = slugify(args.prompt)
    output_path = OUTPUT_DIR / f"{timestamp}_{slug}.png"
    image.save(str(output_path))

    elapsed = time.time() - t_start
    vram_peak = torch.cuda.max_memory_allocated() / 1024**3

    print(f"\n✅ Imagen generada: {output_path}", flush=True)
    print(f"Tiempo: {elapsed:.1f}s | VRAM pico: {format_vram(vram_peak)}", flush=True)

    return str(output_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SDXL Image Generator — Máxima calidad en RTX 5070",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s "un gato siames con camiseta de Argentina"
  %(prog)s "retrato de una mujer en un cafe" --model realvis --mode quality
  %(prog)s "idea rapida" --model turbo --mode fast
  %(prog)s "prompt tecnico" --raw --steps 40 --negative "mis negativos"
        """,
    )
    parser.add_argument("prompt", help="Descripción de la imagen")
    parser.add_argument(
        "--model", choices=list(MODELS.keys()), default="juggernaut",
        help="Modelo a usar (default: juggernaut)"
    )
    parser.add_argument(
        "--mode", choices=["fast", "quality", "max"], default="max",
        help="Modo de calidad (default: max)"
    )
    parser.add_argument("--steps", type=int, help="Override de steps")
    parser.add_argument("--seed", type=int, help="Seed fijo")
    parser.add_argument(
        "--raw", action="store_true",
        help="Deshabilitar prompt engineering automático"
    )
    parser.add_argument("--negative", help="Negative prompt manual")
    parser.add_argument("--output", help="Ruta de salida (default: auto)")

    args = parser.parse_args()

    # Validar modo turbo
    if args.model == "turbo" and args.mode in ("quality", "max"):
        args.mode = "fast"
        print("⚠️  Modo turbo solo soporta 'fast'. Usando fast.", flush=True)

    # Seed
    if args.seed is not None:
        torch.manual_seed(args.seed)
        print(f"Seed: {args.seed}", flush=True)

    output_path = generate(args)

    # Si se especificó output custom, copiar
    if args.output:
        import shutil
        shutil.copy2(output_path, args.output)
        print(f"Copiado a: {args.output}", flush=True)


if __name__ == "__main__":
    main()
