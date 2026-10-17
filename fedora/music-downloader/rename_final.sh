#!/bin/bash

cd /home/glasalvia/Musica

# Separar videos y canciones
videos=()
canciones=()

for file in *.mp4; do
    if [[ -f "$file" ]]; then
        videos+=("$file")
    fi
done

for file in *.mp3; do
    if [[ -f "$file" ]]; then
        canciones+=("$file")
    fi
done

echo "Videos: ${#videos[@]}"
echo "Canciones: ${#canciones[@]}"

# Crear lista final: videos primero, luego canciones
final_list=()
for video in "${videos[@]}"; do
    final_list+=("$video")
done

for cancion in "${canciones[@]}"; do
    final_list+=("$cancion")
done

echo "Lista final: ${#final_list[@]} archivos"

# Renombrar con numeración incremental desde 01
counter=1
for file in "${final_list[@]}"; do
    # Obtener extensión
    ext="${file##*.}"
    # Crear nuevo nombre con numeración
    newname=$(printf "%02d - %s.%s" $counter "${file%.*}" "$ext")
    
    # Evitar sobrescritura si ya existe
    if [ ! -f "$newname" ]; then
        mv "$file" "$newname"
        echo "Renombrado: $file -> $newname"
    else
        echo "Error: $newname ya existe, saltando: $file"
    fi
    
    counter=$((counter + 1))
done

echo "Proceso completado. Total: $((counter - 1)) archivos renombrados"
