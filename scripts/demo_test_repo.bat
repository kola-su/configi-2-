@echo off
rem Граф зависимостей на тестовых репозиториях из каталога examples (этап 3)
chcp 65001 >nul
cd /d "%~dp0\.."
for %%f in (configs\test\*.xml) do (
    echo === %%f ===
    python src\main.py "%%f"
)
