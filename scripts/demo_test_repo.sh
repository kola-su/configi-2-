#!/bin/sh
# Граф зависимостей на тестовых репозиториях из каталога examples (этапы 3 и 5)
cd "$(dirname "$0")/.." || exit 1
for file in configs/test/*.xml; do
    echo "=== $file ==="
    python3 src/main.py "$file"
done
