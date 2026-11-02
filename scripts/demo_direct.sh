#!/bin/sh
# Прямые зависимости реальных пакетов crates.io (этап 2)
cd "$(dirname "$0")/.." || exit 1
for file in config.xml configs/real_*.xml; do
    echo "=== $file ==="
    python3 src/main.py "$file"
done
