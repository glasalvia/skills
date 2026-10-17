---
name: "music-downloader"
description: "Descarga masiva de canciones MP3 desde YouTube usando yt-dlp con numeración automática y metadatos embebidos."
---

# Music Downloader Skill

## Descripción
Herramienta para descargar canciones en formato MP3 desde YouTube utilizando yt-dlp, con numeración automática y organización de archivos.

## Archivos del skill

| Archivo | Rol |
|---------|-----|
| `descargar_canciones.sh` | Script de descarga masiva desde YouTube |
| `rename_final.sh` | Renombrado con numeración incremental (versión final) |
| `rename_musica.sh` | Renombrado con detección de videos y orden específico |
| `SKILL.md` | Documentación del skill |

Todos los scripts operan sobre el directorio `/home/glasalvia/Musica/`.

---

## Procedimiento de descarga

## Requisitos Previos
- yt-dlp instalado (`pip install yt-dlp` o `sudo pacman -S yt-dlp`)
- FFmpeg instalado (`sudo pacman -S ffmpeg`)
- Python 3.x

## Procedimiento

### 1. Verificar Dependencias
```bash
which yt-dlp && yt-dlp --version
which ffmpeg && ffmpeg -version | head -1
```

### 2. Crear Script de Descarga Masiva
Crear archivo `descargar_canciones.sh`:
```bash
#!/bin/bash
OUTPUT_DIR="/home/glasalvia/Musica"
mkdir -p "$OUTPUT_DIR"

CANCIONES=(
    "Artista - Título 1"
    "Artista - Título 2"
    # ... agregar todas las canciones
)

NUMERO=1
for CANCION in "${CANCIONES[@]}"; do
    yt-dlp -x --audio-format mp3 --audio-quality 0 \
        -o "$OUTPUT_DIR/%(playlist_index)s - %(title)s.%(ext)s" \
        "ytsearch1:$CANCION" \
        --no-playlist \
        2>&1 | grep -E "(Downloading|Extracting|Saving)" || echo "Error en: $CANCION"
    NUMERO=$((NUMERO + 1))
done
```

### 3. Ejecutar Descarga
```bash
chmod +x descargar_canciones.sh
bash descargar_canciones.sh
```

### 4. Corrección Manual (Opcional)
Para canciones específicas con URLs conocidas:
```bash
yt-dlp -x --audio-format mp3 --audio-quality 0 \
    -o "$OUTPUT_DIR/NUMERO - TITULO_CORRECTO.%(ext)s" \
    "URL_ESPECIFICA_DE_YOUTUBE"
```

## Parámetros Clave
- `-x`: Extraer solo audio
- `--audio-format mp3`: Formato de salida MP3
- `--audio-quality 0`: Máxima calidad disponible
- `ytsearch1:`: Buscar primera coincidencia en YouTube
- `--no-playlist`: No descargar playlists completas

## Scripts de Renombrado

Los scripts `rename_final.sh` y `rename_musica.sh` se utilizan para reorganizar
los archivos descargados en `/home/glasalvia/Musica/` con numeración incremental.

```bash
chmod +x rename_final.sh
./rename_final.sh
```

`rename_final.sh`: renombra todos los archivos en `/home/glasalvia/Musica/` con
numeración 01, 02, 03... (videos .mp4 primero, luego canciones .mp3).

`rename_musica.sh`: versión alternativa con detección heurística de videos y
posiciones específicas.

## Notas Técnicas
- Los archivos se guardan con numeración automática basada en el índice de playlist de YouTube
- Para corrección precisa, usar URLs directas en lugar de búsquedas
- El proceso puede tomar 15-20 minutos para 27 canciones dependiendo de la velocidad de conexión
