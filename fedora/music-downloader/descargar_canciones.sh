#!/bin/bash

# Directorio de salida
OUTPUT_DIR="/home/glasalvia/Musica"
mkdir -p "$OUTPUT_DIR"

# Lista de canciones (formato: "artista - titulo")
CANCIONES=(
)

# Contador
NUMERO=1

echo "=== INICIO DE DESCARGA MASIVA ==="
echo "Directorio: $OUTPUT_DIR"
echo "Total de canciones: ${#CANCIONES[@]}"
echo ""

for CANCION in "${CANCIONES[@]}"; do
    echo "--- [$NUMERO/${#CANCIONES[@]}] Descargando: $CANCION ---"
    
    # Buscar en YouTube y descargar MP3 con numeración automática
    yt-dlp -x --audio-format mp3 --audio-quality 0 \
        -o "$OUTPUT_DIR/%(playlist_index)s - %(title)s.%(ext)s" \
        --yes-playlist \
        "ytsearch1:$CANCION" \
        --no-playlist \
        2>&1 | grep -E "(Downloading|Extracting|Saving)" || echo "Error en: $CANCION"
    
    echo ""
    NUMERO=$((NUMERO + 1))
done

echo "=== PROCESO COMPLETADO ==="
echo "Archivos descargados en: $OUTPUT_DIR"
ls -lh "$OUTPUT_DIR" | head -20

