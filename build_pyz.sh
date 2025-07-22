#!/bin/bash

# === Конфигурация ===
PROJECT_DIR="src"
ENTRY_POINT="main:main"    # модуль и функция запуска
OUTPUT_FILE="app.pyz"      # имя итогового файла

# === 1. Очистка старых артефактов ===
echo "Очистка старых артефактов..."
find "$PROJECT_DIR" -name "*.pyc" -delete
find "$PROJECT_DIR" -name "__pycache__" -type d -exec rm -rf {} +

# === 2. Компиляция в байткод ===
echo "Компиляция .py → .pyc..."
python3 -m compileall "$PROJECT_DIR"

# === 3. Удаление исходников .py ===
echo "Удаление исходных .py..."
find "$PROJECT_DIR" -name "*.py" -delete

# === 4. Упаковка в .pyz ===
echo "Создание .pyz архива..."
python3 -m zipapp "$PROJECT_DIR" -m "$ENTRY_POINT" -o "$OUTPUT_FILE"

# === 5. Делаем исполняемым ===
chmod +x "$OUTPUT_FILE"

echo "✅ Готово! Файл: $OUTPUT_FILE"
echo "Запуск: ./app.pyz или python3 app.pyz"