#!/bin/sh
# Демонстрация обработки ошибок конфигурации (этап 1)
cd "$(dirname "$0")/.." || exit 1
echo "=== корректный config.xml ==="
python3 src/main.py config.xml
echo "=== файл конфигурации не существует ==="
python3 src/main.py configs/no_such_config.xml
for file in configs/errors/*.xml; do
    echo "=== $file ==="
    python3 src/main.py "$file"
done
