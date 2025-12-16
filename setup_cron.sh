#!/bin/bash

# Скрипт для настройки автоматического удаления отчётов через cron
# Использование: ./setup_cron.sh [--force]
#   --force  - автоматически заменить существующую задачу без запроса подтверждения

set -e

FORCE=false
if [ "$1" == "--force" ]; then
    FORCE=true
fi

# Определяем директорию скрипта (директорию проекта)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

echo "=== Настройка cron для автоматического удаления отчётов ==="
echo "Директория проекта: $PROJECT_DIR"

# Проверяем наличие manage.py
if [ ! -f "$PROJECT_DIR/manage.py" ]; then
    echo "Ошибка: файл manage.py не найден в $PROJECT_DIR"
    exit 1
fi

# Ищем Python в виртуальном окружении
PYTHON_PATH=""
if [ -f "$PROJECT_DIR/env/bin/python" ]; then
    PYTHON_PATH="$PROJECT_DIR/env/bin/python"
elif [ -f "$PROJECT_DIR/venv/bin/python" ]; then
    PYTHON_PATH="$PROJECT_DIR/venv/bin/python"
elif [ -f "$PROJECT_DIR/.venv/bin/python" ]; then
    PYTHON_PATH="$PROJECT_DIR/.venv/bin/python"
else
    # Используем системный python3
    PYTHON_PATH=$(which python3)
    if [ -z "$PYTHON_PATH" ]; then
        echo "Ошибка: Python не найден"
        exit 1
    fi
    echo "Внимание: используется системный Python ($PYTHON_PATH)"
    echo "Рекомендуется использовать виртуальное окружение"
fi

echo "Python: $PYTHON_PATH"

# Проверяем наличие команды delete_expired_reports
echo "Проверка команды delete_expired_reports..."
if ! $PYTHON_PATH "$PROJECT_DIR/manage.py" delete_expired_reports --help > /dev/null 2>&1; then
    echo "Ошибка: команда delete_expired_reports не найдена"
    exit 1
fi
echo "Команда найдена ✓"

# Создаём директорию для логов
LOGS_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOGS_DIR"
echo "Директория логов: $LOGS_DIR ✓"

# Формируем команду для cron
CRON_COMMAND="*/5 * * * * cd $PROJECT_DIR && $PYTHON_PATH manage.py delete_expired_reports >> $LOGS_DIR/delete_reports.log 2>&1"

# Проверяем, существует ли уже такая задача в crontab
EXISTING_CRON=$(crontab -l 2>/dev/null | grep "delete_expired_reports" || true)

if [ -n "$EXISTING_CRON" ]; then
    echo ""
    echo "Внимание: задача для delete_expired_reports уже существует в crontab:"
    echo "$EXISTING_CRON"
    echo ""
    if [ "$FORCE" = true ]; then
        # Автоматически заменяем существующую задачу
        (crontab -l 2>/dev/null | grep -v "delete_expired_reports"; echo "$CRON_COMMAND") | crontab -
        echo "Задача обновлена ✓"
    else
        read -p "Заменить существующую задачу? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Удаляем старую задачу и добавляем новую
            (crontab -l 2>/dev/null | grep -v "delete_expired_reports"; echo "$CRON_COMMAND") | crontab -
            echo "Задача обновлена ✓"
        else
            echo "Отмена. Задача не изменена."
            exit 0
        fi
    fi
else
    # Добавляем новую задачу
    (crontab -l 2>/dev/null; echo "$CRON_COMMAND") | crontab -
    echo "Задача добавлена в crontab ✓"
fi

# Показываем текущий crontab
echo ""
echo "Текущие задачи cron для удаления отчётов:"
crontab -l | grep "delete_expired_reports" || echo "Не найдено"

echo ""
echo "=== Настройка завершена ==="
echo ""
echo "Задача будет выполняться каждые 5 минут."
echo "Логи будут сохраняться в: $LOGS_DIR/delete_reports.log"
echo ""
echo "Полезные команды:"
echo "  Просмотр логов: tail -f $LOGS_DIR/delete_reports.log"
echo "  Проверка задач: crontab -l"
echo "  Проверка отчётов: $PYTHON_PATH $PROJECT_DIR/manage.py check_pending_deletion"
echo "  Тестовый запуск: $PYTHON_PATH $PROJECT_DIR/manage.py delete_expired_reports --dry-run"

