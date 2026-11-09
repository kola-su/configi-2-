@echo off
rem Сравнение порядка загрузки с настоящим Cargo (нужен установленный Rust)
chcp 65001 >nul
cd /d "%~dp0\.."
python scripts\cargo_compare.py examples\simple.txt A
python scripts\cargo_compare.py examples\simple.txt C
python scripts\cargo_compare.py examples\chain.txt A
python scripts\cargo_compare.py examples\names.txt APP
python scripts\cargo_compare.py examples\cycle.txt A
