# Шуточная энциклопедия о друге

Проект из трёх частей:
1. `exporter/`: экспорт личного диалога Telegram в Termux (официальный API, Telethon).
2. Анализ переписки и база знаний (будет добавлено).
3. Локальный сайт в стиле вики (будет добавлено).

## Приватность

В репозитории лежит только код. Переписка, фото, `api_hash` и файл сессии
хранятся только на телефоне (`~/telegram_archive`, `~/.tg_export`) и исключены через `.gitignore`.

## Установка (Termux)

```
pkg install -y git
git clone -b claude/telegram-friend-encyclopedia-xacgdi https://github.com/novrynyxx-cyber/Hgf ~/Hgf
bash ~/Hgf/setup.sh
```

## Использование

```
cd ~/Hgf/exporter
python tg_export.py --limit 50     # пробный запуск
python tg_export.py                # полный экспорт, повторный запуск докачивает
python tg_export.py --media photos # только фото
python tg_export.py --max-mb 200   # разрешить файлы до 200 МБ
python tg_export.py pack           # zip с текстом (без медиа) в «Загрузки»
```

Структура архива `~/telegram_archive/`: `messages.jsonl`, `messages.txt`, `manifest.json`,
`chat.json`, `media/{photos,videos,voice,audio,stickers,documents}/<id сообщения>.<расширение>`.
