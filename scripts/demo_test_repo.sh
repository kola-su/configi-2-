#!/bin/sh
# Граф зависимостей на тестовых репозиториях из каталога examples (этап 3)
cd "$(dirname "$0")/.." || exit 1
for file in configs/test/*.xml; do
    echo "=== $file ==="
    python3 src/main.py "$file"
done
