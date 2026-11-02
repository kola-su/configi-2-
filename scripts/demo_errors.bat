@echo off
rem Демонстрация обработки ошибок конфигурации (этап 1)
chcp 65001 >nul
cd /d "%~dp0\.."
echo === корректный config.xml ===
python src\main.py config.xml
echo === файл конфигурации не существует ===
python src\main.py configs\no_such_config.xml
for %%f in (configs\errors\*.xml) do (
    echo === %%f ===
    python src\main.py "%%f"
)
