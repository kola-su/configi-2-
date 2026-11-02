@echo off
rem Прямые зависимости реальных пакетов crates.io (этап 2)
chcp 65001 >nul
cd /d "%~dp0\.."
for %%f in (config.xml configs\real_*.xml) do (
    echo === %%f ===
    python src\main.py "%%f"
)
