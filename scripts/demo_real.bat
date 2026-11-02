@echo off
rem Графы зависимостей реальных пакетов crates.io (нужен интернет)
chcp 65001 >nul
cd /d "%~dp0\.."
for %%f in (config.xml configs\real_*.xml) do (
    echo === %%f ===
    python src\main.py "%%f"
)
