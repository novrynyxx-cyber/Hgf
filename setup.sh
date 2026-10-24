#!/data/data/com.termux/files/usr/bin/bash
# Установка программы экспорта в Termux. Запуск: bash ~/Hgf/setup.sh
set -e
echo "== Устанавливаю Python и зависимости =="
pkg install -y python
pip install --upgrade -r "$(dirname "$0")/exporter/requirements.txt"
python -c "import telethon; print('Telethon', telethon.__version__, '— установлен')"
[ -d "$HOME/storage/downloads" ] || echo "Совет: выполните termux-setup-storage, чтобы архив можно было положить в «Загрузки»."
echo
echo "Готово. Пробный запуск (50 сообщений):"
echo "  cd ~/Hgf/exporter && python tg_export.py --limit 50"
