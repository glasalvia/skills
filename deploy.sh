#!/bin/bash
# deploy.sh — Skills Repository Deployer
# Genera symlinks desde workspace/skills/ → skills repo
# Uso: ./deploy.sh [--dry-run]

set -euo pipefail

REPO_DIR="$HOME/skills"
WORKSPACE_SKILLS="$HOME/.openclaw/workspace/skills"
HOSTNAME=$(uname -n)
DRY_RUN=false

if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=true
    echo "🔍 DRY RUN — no se modificarán archivos"
fi

# Determinar qué skills aplicar según hostname
case "$HOSTNAME" in
    cachy-gla|cachy*)
        CATEGORIES="shared cachy-gla"
        echo "📦 Desplegando para: cachy-gla"
        ;;
    raspberry*|raspi*)
        CATEGORIES="shared raspi"
        echo "📦 Desplegando para: Raspi"
        ;;
    *)
        echo "⚠️  Hostname $HOSTNAME no reconocido. Usando solo shared/"
        CATEGORIES="shared"
        ;;
esac

# Crear workspace/skills si no existe
[ -d "$WORKSPACE_SKILLS" ] || mkdir -p "$WORKSPACE_SKILLS"

SYMLINKS_CREATED=0
SYMLINKS_SKIPPED=0

for category in $CATEGORIES; do
    SRC="$REPO_DIR/$category"
    if [ ! -d "$SRC" ]; then
        echo "⚠️  Categoría $category no encontrada en $SRC, saltando"
        continue
    fi

    for skill_dir in "$SRC"/*/; do
        skill_name=$(basename "$skill_dir")
        TARGET="$WORKSPACE_SKILLS/$skill_name"

        if [ -L "$TARGET" ]; then
            # Ya existe un symlink — verificar que apunte al repo
            CURRENT_TARGET=$(readlink "$TARGET")
            if [ "$CURRENT_TARGET" = "$skill_dir" ]; then
                echo "   = $skill_name (ya correcto)"
                SYMLINKS_SKIPPED=$((SYMLINKS_SKIPPED + 1))
                continue
            else
                echo "   ~ $skill_name (reemplazando: $CURRENT_TARGET → $skill_dir)"
                if [ "$DRY_RUN" = false ]; then
                    rm "$TARGET"
                    ln -sfn "$skill_dir" "$TARGET"
                    SYMLINKS_CREATED=$((SYMLINKS_CREATED + 1))
                fi
            fi
        elif [ -d "$TARGET" ] && [ ! -L "$TARGET" ]; then
            # Directorio real — renombrar a .bak y reemplazar con symlink
            echo "   ! $skill_name (respaldo y symlink)"
            if [ "$DRY_RUN" = false ]; then
                mv "$TARGET" "${TARGET}.bak.$(date +%s)"
                ln -sfn "$skill_dir" "$TARGET"
                SYMLINKS_CREATED=$((SYMLINKS_CREATED + 1))
            fi
        else
            echo "   + $skill_name (nuevo symlink)"
            if [ "$DRY_RUN" = false ]; then
                ln -sfn "$skill_dir" "$TARGET"
                SYMLINKS_CREATED=$((SYMLINKS_CREATED + 1))
            fi
        fi
    done
done

echo ""
echo "📊 Resumen: $SYMLINKS_CREATED creados, $SYMLINKS_SKIPPED existentes"
echo "✅ Deploy completado para $HOSTNAME"
