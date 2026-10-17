#!/bin/bash
# Останавливает старую копию скрипта расшифровки и запускает новую. Двойной клик в Finder.
cd "$(dirname "$0")/_scripts" || exit 1
pkill -f "07-prototip-produkta/_scripts/run.py" 2>/dev/null
sleep 2
echo "Старая копия остановлена. Запускаю run.py (окно не закрывать, ноутбук на зарядке)…"
exec caffeinate -i python3 "$PWD/run.py"
