#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

DB_NAME="park_ads"

echo "1) PostgreSQL"
if ! command -v psql >/dev/null 2>&1; then
    echo "   ошибка: psql не найден. Установи: brew install postgresql@17"
    exit 1
fi
if brew services list | grep -q "postgresql@17.*started"; then
    echo "   уже запущен"
else
    echo "   не запущен, стартую (brew services start postgresql@17)"
    brew services start postgresql@17
    sleep 3
fi

echo "2) База данных '$DB_NAME'"
if psql -lqt | cut -d '|' -f 1 | grep -qw "$DB_NAME"; then
    echo "   уже существует"
else
    echo "   не найдена, создаю (createdb $DB_NAME)"
    createdb "$DB_NAME"
fi

echo "3) Python-окружение (.venv)"
if [ ! -d ".venv" ]; then
    echo "   не найдено, создаю и ставлю зависимости (может занять минуту)"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -q -r requirements.txt
else
    echo "   уже есть"
    source .venv/bin/activate
fi

echo "4) Схема и данные"
TABLE_COUNT=$(psql -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
if [ "$TABLE_COUNT" -eq 0 ]; then
    echo "   таблиц нет, накатываю схему и справочные данные"
    psql -d "$DB_NAME" -f db/schema.sql
    psql -d "$DB_NAME" -f db/seed_reference_data.sql
    echo "   генерирую трафик/размещения (db/generate_data.py)"
    python3 db/generate_data.py
else
    ROW_COUNT=$(psql -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM zone_traffic;")
    if [ "$ROW_COUNT" -eq 0 ]; then
        echo "   таблицы пустые, генерирую данные"
        python3 db/generate_data.py
    else
        echo "   данные на месте ($ROW_COUNT строк трафика)"
    fi
fi

mkdir -p "$HOME/.streamlit"
if [ ! -f "$HOME/.streamlit/credentials.toml" ]; then
    printf '[general]\nemail = ""\n' > "$HOME/.streamlit/credentials.toml"
fi

echo "5) Запускаю дашборд - http://localhost:8501 (Ctrl+C, чтобы остановить)"
streamlit run dashboard/app.py
