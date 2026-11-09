#!/bin/sh
# Сравнение порядка загрузки с настоящим Cargo (нужен установленный Rust)
cd "$(dirname "$0")/.." || exit 1
python3 scripts/cargo_compare.py examples/simple.txt A
python3 scripts/cargo_compare.py examples/simple.txt C
python3 scripts/cargo_compare.py examples/chain.txt A
python3 scripts/cargo_compare.py examples/names.txt APP
python3 scripts/cargo_compare.py examples/cycle.txt A
