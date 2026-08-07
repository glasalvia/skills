#!/bin/bash
# Wrapper para ejecutar scripts del pipeline con venv activado
set -e
cd /home/glasalvia/facturas
source venv/bin/activate
exec python3 "$@"
