#!/bin/sh
# Графы зависимостей реальных пакетов crates.io (нужен интернет)
cd "$(dirname "$0")/.." || exit 1
for file in config.xml configs/real_*.xml; do
    echo "=== $file ==="
    python3 src/main.py "$file"
done
