#!/bin/bash

cd /home/glasalvia/Musica

# Identificar videos (archivos con [HD] o similar)
videos=()
others=()

for file in *.mp3; do
    if [[ "$file" == *"[HD]"* ]] || [[ "$file" == *"video"* ]] || [[ "$file" == *"Video"* ]]; then
        videos+=("$file")
    else
        others+=("$file")
    fi
done

echo "Videos encontrados: ${#videos[@]}"
echo "Canciones encontradas: ${#others[@]}"

# Crear lista final con posiciones de videos especificadas
final_list=()

# Posición 2: primer video (índice 1 en array 0-based)
if [ ${#videos[@]} -ge 1 ]; then
    final_list+=("${videos[0]}")
fi

# Agregar primeras canciones hasta antes del segundo video
count=0
for i in "${!others[@]}"; do
    if [ $count -eq 1 ] && [ ${#videos[@]} -ge 2 ]; then
        final_list+=("${videos[1]}")
        count=$((count + 1))
    fi
    if [ $count -lt 2 ]; then
        final_list+=("${others[$i]}")
        count=$((count + 1))
    fi
done

# Agregar videos restantes y canciones finales
for i in "${!videos[@]}"; do
    if [ $i -ge 2 ]; then
        final_list+=("${videos[$i]}")
    fi
done

# Completar con canciones restantes
for i in "${!others[@]}"; do
    already_added=false
    for j in "${final_list[@]}"; do
        if [ "$j" == "${others[$i]}" ]; then
            already_added=true
            break
        fi
    done
    if [ "$already_added" = false ]; then
        final_list+=("${others[$i]}")
    fi
done

echo "Lista final: ${#final_list[@]} archivos"

# Renombrar con numeración incremental
counter=1
for file in "${final_list[@]}"; do
    newname=$(printf "%02d - %s" $counter "${file}")
    if [ "$file" != "$newname" ]; then
        mv "$file" "$newname"
        echo "Renombrado: $file -> $newname"
    fi
    counter=$((counter + 1))
done

echo "Proceso completado. Total: $((counter - 1)) archivos renombrados"
