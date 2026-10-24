#!/usr/bin/env python3
"""
Экспорт личного диалога Telegram в локальный архив (официальный API, Telethon).

Запуск в Termux:
    python tg_export.py --limit 50     # пробный запуск: только 50 сообщений
    python tg_export.py                # полный экспорт (докачивает недостающее)
    python tg_export.py --pick         # выбрать другой диалог
    python tg_export.py pack           # упаковать ТЕКСТ (без медиа) для анализа

Секреты (api_id, api_hash, файл сессии) хранятся только в ~/.tg_export/
и никуда не отправляются.
"""

import argparse
import asyncio
import getpass
import json
import os
import shutil
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
SECRETS_DIR = HOME / ".tg_export"
CONFIG_FILE = SECRETS_DIR / "config.json"
SESSION_FILE = SECRETS_DIR / "session"
DEFAULT_ARCHIVE = HOME / "telegram_archive"

MEDIA_DIRS = {
    "photo": "photos",
    "video": "videos",
    "video_note": "videos",
    "gif": "videos",
    "voice": "voice",
    "audio": "audio",
    "sticker": "stickers",
    "document": "documents",
}
DEFAULT_EXT = {
    "photo": ".jpg", "video": ".mp4", "video_note": ".mp4", "gif": ".mp4",
    "voice": ".ogg", "audio": ".mp3", "sticker": ".webp", "document": ".bin",
}
MAX_RETRIES = 8


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- секреты

def load_or_ask_config():
    SECRETS_DIR.mkdir(mode=0o700, exist_ok=True)
    if CONFIG_FILE.exists():
        cfg = json.loads(CONFIG_FILE.read_text())
        if cfg.get("api_id") and cfg.get("api_hash"):
            return int(cfg["api_id"]), cfg["api_hash"]
    log("Нужны api_id и api_hash с https://my.telegram.org (API development tools).")
    log("Они сохранятся только на этом телефоне, в " + str(CONFIG_FILE))
    while True:
        api_id = input("api_id (число): ").strip()
        if api_id.isdigit():
            break
        log("api_id должен состоять только из цифр.")
    log("\nСейчас вставьте api_hash и нажмите Enter.")
    log("ВНИМАНИЕ: символы НЕ отображаются на экране — так и задумано, программа не зависла.")
    while True:
        api_hash = getpass.getpass("api_hash: ").strip()
        if len(api_hash) == 32 and all(c in "0123456789abcdef" for c in api_hash.lower()):
            break
        log("Это не похоже на api_hash (должно быть 32 символа 0-9 и a-f). Попробуйте ещё раз.")
    CONFIG_FILE.write_text(json.dumps({"api_id": int(api_id), "api_hash": api_hash}))
    os.chmod(CONFIG_FILE, 0o600)
    return int(api_id), api_hash


# ---------------------------------------------------------------- хранилище

class Archive:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        for d in set(MEDIA_DIRS.values()):
            (self.root / "media" / d).mkdir(parents=True, exist_ok=True)
        self.jsonl = self.root / "messages.jsonl"
        self.chat_file = self.root / "chat.json"
        self.records = {}  # id -> record
        self._load()

    def _load(self):
        if not self.jsonl.exists():
            return
        bad = 0
        with self.jsonl.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    self.records[rec["id"]] = rec
                except (json.JSONDecodeError, KeyError):
                    bad += 1  # обрыв записи при аварийном завершении
        if bad:
            log(f"Найдено {bad} повреждённых строк (обрыв прошлого запуска) — исправляю.")
            self.rewrite()

    def rewrite(self):
        tmp = self.jsonl.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for mid in sorted(self.records):
                f.write(json.dumps(self.records[mid], ensure_ascii=False) + "\n")
        tmp.replace(self.jsonl)

    def max_id(self):
        return max(self.records) if self.records else 0

    def append(self, recs):
        new = [r for r in recs if r["id"] not in self.records]
        if not new:
            return 0
        with self.jsonl.open("a", encoding="utf-8") as f:
            for r in new:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                self.records[r["id"]] = r
            f.flush()
            os.fsync(f.fileno())
        return len(new)

    def load_chat(self):
        if self.chat_file.exists():
            return json.loads(self.chat_file.read_text(encoding="utf-8"))
        return None

    def save_chat(self, info):
        self.chat_file.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- сообщение -> запись

def display_name(entity):
    if entity is None:
        return None
    first = getattr(entity, "first_name", None) or ""
    last = getattr(entity, "last_name", None) or ""
    name = (first + " " + last).strip()
    return name or getattr(entity, "title", None) or getattr(entity, "username", None)


def media_kind(msg):
    if getattr(msg, "photo", None):
        return "photo"
    for kind in ("video_note", "voice", "gif", "sticker", "video", "audio"):
        if getattr(msg, kind, None):
            return kind
    if getattr(msg, "document", None):
        return "document"
    return None


def iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def message_to_record(msg, names):
    sender_id = getattr(msg, "sender_id", None)
    rec = {
        "id": msg.id,
        "date": iso(msg.date),
        "date_local": msg.date.astimezone().strftime("%Y-%m-%d %H:%M:%S") if msg.date else None,
        "sender_id": sender_id,
        "sender": names.get(sender_id) or display_name(getattr(msg, "sender", None)),
        "out": bool(getattr(msg, "out", False)),
        "text": getattr(msg, "message", None) or "",
    }
    if getattr(msg, "reply_to_msg_id", None):
        rec["reply_to"] = msg.reply_to_msg_id
    if getattr(msg, "edit_date", None):
        rec["edited"] = iso(msg.edit_date)
    if getattr(msg, "grouped_id", None):
        rec["album"] = str(msg.grouped_id)
    fwd = getattr(msg, "fwd_from", None)
    if fwd is not None:
        rec["forwarded_from"] = getattr(fwd, "from_name", None) or "переслано"
    action = getattr(msg, "action", None)
    if action is not None:
        rec["service"] = type(action).__name__.replace("MessageAction", "")
        if getattr(action, "duration", None):
            rec["service_duration"] = action.duration
    reactions = getattr(msg, "reactions", None)
    if reactions is not None and getattr(reactions, "results", None):
        rec["reactions"] = [
            {"emoji": getattr(r.reaction, "emoticon", "?"), "count": r.count}
            for r in reactions.results
        ]
    if getattr(msg, "poll", None):
        try:
            rec["poll"] = msg.poll.poll.question.text if hasattr(msg.poll.poll.question, "text") \
                else str(msg.poll.poll.question)
        except AttributeError:
            rec["poll"] = "опрос"
    if getattr(msg, "geo", None):
        rec["other_media"] = "геолокация (не сохраняется)"
    elif getattr(msg, "contact", None):
        rec["other_media"] = "контакт (не сохраняется)"
    wp = getattr(msg, "web_preview", None)
    if wp is not None and getattr(wp, "url", None):
        rec["link_preview"] = {"url": wp.url, "title": getattr(wp, "title", None)}

    kind = media_kind(msg)
    if kind:
        f = msg.file
        ext = (getattr(f, "ext", None) or DEFAULT_EXT[kind]) if kind != "photo" else ".jpg"
        rec["media"] = {
            "type": kind,
            "path": f"media/{MEDIA_DIRS[kind]}/{msg.id}{ext}",
            "size": getattr(f, "size", None),
            "mime": getattr(f, "mime_type", None),
            "name": getattr(f, "name", None),
            "duration": getattr(f, "duration", None),
        }
    return rec


# ---------------------------------------------------------------- повторы при ошибках

async def with_retries(what, coro_factory):
    from telethon import errors
    delay = 2
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await coro_factory()
        except errors.FloodWaitError as e:
            log(f"Telegram просит подождать {e.seconds} с ({what}). Жду...")
            await asyncio.sleep(e.seconds + 1)
        except (ConnectionError, OSError, asyncio.TimeoutError, errors.ServerError,
                errors.RpcCallFailError) as e:
            if attempt == MAX_RETRIES:
                raise
            log(f"Временная ошибка ({what}): {type(e).__name__}. Повтор через {delay} с "
                f"[{attempt}/{MAX_RETRIES}]")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 120)
    raise RuntimeError(f"Не удалось выполнить: {what}")


# ---------------------------------------------------------------- выбор диалога

async def pick_dialog(client):
    log("\nЗагружаю список личных диалогов...")
    dialogs = []
    async for d in client.iter_dialogs():
        ent = d.entity
        if d.is_user and not getattr(ent, "bot", False) and not getattr(ent, "is_self", False):
            dialogs.append(d)
    if not dialogs:
        raise SystemExit("Личных диалогов не найдено.")
    query = input("Введите часть имени друга (или Enter, чтобы показать первые 30): ").strip().lower()
    shown = [d for d in dialogs if query in (d.name or "").lower()
             or query in (getattr(d.entity, "username", None) or "").lower()] if query else dialogs[:30]
    if not shown:
        raise SystemExit("Никого не нашлось. Запустите ещё раз и введите другое имя.")
    for i, d in enumerate(shown, 1):
        uname = getattr(d.entity, "username", None)
        log(f"  {i:>2}. {d.name}" + (f" (@{uname})" if uname else ""))
    while True:
        choice = input("Номер нужного диалога: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(shown):
            return shown[int(choice) - 1].entity
        log("Введите номер из списка.")


async def resolve_saved_entity(client, chat):
    try:
        return await client.get_entity(chat["peer_id"])
    except (ValueError, TypeError):
        async for d in client.iter_dialogs():
            if d.id == chat["peer_id"]:
                return d.entity
    raise SystemExit("Сохранённый диалог не найден. Запустите с --pick.")


# ---------------------------------------------------------------- экспорт текста

async def export_messages(client, entity, archive, names, limit=None):
    start_after = archive.max_id()
    if start_after:
        log(f"Уже сохранено {len(archive.records)} сообщений. Докачиваю новые (после id {start_after})...")
    else:
        log("Начинаю выгрузку с самого первого сообщения...")
    fetched = 0
    t0 = time.time()
    attempt_delay = 2
    while True:
        batch = []
        try:
            async for msg in client.iter_messages(entity, reverse=True, offset_id=archive.max_id(),
                                                  limit=(limit - fetched) if limit else None,
                                                  wait_time=1):
                batch.append(message_to_record(msg, names))
                fetched += 1
                if len(batch) >= 200:
                    archive.append(batch)
                    batch = []
                    rate = fetched / max(time.time() - t0, 1)
                    log(f"  сохранено {len(archive.records)} (≈{rate:.0f} сообщ./с), "
                        f"последнее от {msg.date:%Y-%m-%d}")
            archive.append(batch)
            break
        except KeyboardInterrupt:
            archive.append(batch)
            raise
        except Exception as e:  # временные сбои: сохраняем то, что есть, и продолжаем с места остановки
            archive.append(batch)
            from telethon import errors
            if isinstance(e, errors.FloodWaitError):
                log(f"Telegram просит подождать {e.seconds} с. Жду...")
                await asyncio.sleep(e.seconds + 1)
                continue
            if attempt_delay > 120:
                raise
            log(f"Ошибка при выгрузке: {type(e).__name__}: {e}. Продолжу через {attempt_delay} с.")
            await asyncio.sleep(attempt_delay)
            attempt_delay *= 2
            if not client.is_connected():
                await client.connect()
    log(f"Новых сообщений за этот запуск: {fetched}. Всего в архиве: {len(archive.records)}.")
    return fetched


# ---------------------------------------------------------------- медиа

def media_wanted(rec, mode, max_bytes):
    m = rec.get("media")
    if not m or mode == "none":
        return False
    if mode == "photos" and m["type"] != "photo":
        return False
    if m["type"] != "photo" and m.get("size") and m["size"] > max_bytes:
        return False
    return True


async def download_media(client, entity, archive, mode, max_bytes, only_ids=None):
    todo = [r for r in archive.records.values()
            if media_wanted(r, mode, max_bytes) and not (archive.root / r["media"]["path"]).exists()
            and (only_ids is None or r["id"] in only_ids)]
    if not todo:
        log("Все нужные медиафайлы уже скачаны.")
        return 0, []
    total_mb = sum((r["media"].get("size") or 0) for r in todo) / 1e6
    log(f"Нужно скачать медиафайлов: {len(todo)} (≈{total_mb:.0f} МБ).")
    todo.sort(key=lambda r: r["id"])
    done, failed = 0, []
    for i in range(0, len(todo), 50):
        chunk = todo[i:i + 50]
        ids = [r["id"] for r in chunk]
        # свежие объекты сообщений: у старых ссылок на файлы истекает срок
        msgs = await with_retries("получение сообщений с медиа",
                                  lambda: client.get_messages(entity, ids=ids))
        by_id = {m.id: m for m in msgs if m is not None}
        for rec in chunk:
            msg = by_id.get(rec["id"])
            if msg is None or msg.media is None:
                failed.append((rec["id"], "сообщение или файл больше недоступны"))
                continue
            target = archive.root / rec["media"]["path"]
            part = target.with_name(target.name + ".part")
            try:
                async def dl():
                    with part.open("wb") as fh:
                        await client.download_media(msg, file=fh)
                await with_retries(f"скачивание {target.name}", dl)
                if part.stat().st_size == 0:
                    part.unlink()
                    failed.append((rec["id"], "пустой файл"))
                    continue
                part.replace(target)
                done += 1
            except Exception as e:
                if part.exists():
                    part.unlink()
                failed.append((rec["id"], f"{type(e).__name__}: {e}"))
        log(f"  медиа: {done} скачано, {len(failed)} ошибок, осталось {len(todo) - i - len(chunk)}")
    return done, failed


# ---------------------------------------------------------------- отчёт и проверка

def write_txt(archive):
    out = archive.root / "messages.txt"
    with out.open("w", encoding="utf-8") as f:
        for mid in sorted(archive.records):
            r = archive.records[mid]
            parts = []
            if r.get("forwarded_from"):
                parts.append(f"[переслано от {r['forwarded_from']}]")
            if r.get("reply_to"):
                parts.append(f"[ответ на #{r['reply_to']}]")
            if r.get("service"):
                parts.append(f"[служебное: {r['service']}]")
            if r.get("media"):
                m = r["media"]
                exists = (archive.root / m["path"]).exists()
                parts.append(f"[{m['type']}: {m['path']}{'' if exists else ' — не скачано'}]")
            if r.get("other_media"):
                parts.append(f"[{r['other_media']}]")
            if r.get("poll"):
                parts.append(f"[опрос: {r['poll']}]")
            if r.get("text"):
                parts.append(r["text"])
            f.write(f"#{mid} [{r['date_local']}] {r.get('sender') or '?'}: {' '.join(parts)}\n")


def build_manifest(archive, chat, server_total, mode, max_bytes, failed):
    recs = archive.records.values()
    by_sender, media = {}, {}
    for r in recs:
        by_sender[r.get("sender") or "?"] = by_sender.get(r.get("sender") or "?", 0) + 1
        m = r.get("media")
        if m:
            st = media.setdefault(m["type"], {"всего": 0, "скачано": 0, "не_нужно_по_настройкам": 0,
                                              "не_скачано": 0})
            st["всего"] += 1
            if (archive.root / m["path"]).exists():
                st["скачано"] += 1
            elif not media_wanted(r, mode, max_bytes):
                st["не_нужно_по_настройкам"] += 1
            else:
                st["не_скачано"] += 1
    dates = sorted(r["date"] for r in recs if r.get("date"))
    saved = len(archive.records)
    missing_media = sum(s["не_скачано"] for s in media.values())
    text_complete = server_total is not None and saved >= server_total
    manifest = {
        "создан": datetime.now(timezone.utc).isoformat(),
        "диалог": chat,
        "сообщений_на_сервере": server_total,
        "сообщений_в_архиве": saved,
        "текст_полный": text_complete,
        "первое_сообщение": dates[0] if dates else None,
        "последнее_сообщение": dates[-1] if dates else None,
        "по_авторам": by_sender,
        "медиа": media,
        "режим_медиа": mode,
        "лимит_размера_МБ": max_bytes // 1_000_000,
        "ошибки_медиа": [{"id": i, "причина": why} for i, why in failed][:500],
    }
    (archive.root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest, text_complete, missing_media


def print_report(manifest, text_complete, missing_media, test_mode):
    log("\n================ ПРОВЕРКА АРХИВА ================")
    log(f"Сообщений на сервере Telegram: {manifest['сообщений_на_сервере']}")
    log(f"Сообщений в архиве:            {manifest['сообщений_в_архиве']}")
    log(f"Период: {manifest['первое_сообщение']} — {manifest['последнее_сообщение']}")
    for who, n in manifest["по_авторам"].items():
        log(f"  {who}: {n}")
    for kind, st in manifest["медиа"].items():
        log(f"  {kind}: всего {st['всего']}, скачано {st['скачано']}, "
            f"пропущено по настройкам {st['не_нужно_по_настройкам']}, не скачано {st['не_скачано']}")
    if test_mode:
        log("\nЭто был ПРОБНЫЙ запуск. Архив заведомо неполный.")
    elif text_complete and missing_media == 0:
        log("\nИТОГ: все сообщения, которые отдаёт сервер, сохранены; все нужные медиа скачаны.")
    else:
        if not text_complete:
            log("\nИТОГ: сохранены НЕ все сообщения. Запустите программу ещё раз — она докачает.")
        if missing_media:
            log(f"ИТОГ: не скачано медиафайлов: {missing_media}. Причины — в manifest.json "
                "(«ошибки_медиа»). Повторный запуск попробует снова.")
    log("Учтите: удалённые сообщения и файлы с истёкшим сроком хранения Telegram не отдаёт.")
    log("=================================================\n")


# ---------------------------------------------------------------- упаковка для анализа

def pack(archive_root: Path):
    if not (archive_root / "messages.jsonl").exists():
        raise SystemExit("Архив не найден. Сначала выполните экспорт.")
    downloads = HOME / "storage" / "downloads"
    target_dir = downloads if downloads.exists() else archive_root
    target = target_dir / "telegram_text_archive.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("messages.jsonl", "messages.txt", "manifest.json"):
            p = archive_root / name
            if p.exists():
                z.write(p, name)
    log(f"Готово: {target} ({target.stat().st_size / 1e6:.1f} МБ). Внутри только текст, без фото.")
    if target_dir == downloads:
        log("Файл лежит в папке «Загрузки» (Download) телефона.")


# ---------------------------------------------------------------- main

async def run(args):
    from telethon import TelegramClient
    api_id, api_hash = load_or_ask_config()
    archive = Archive(Path(args.archive).expanduser())
    client = TelegramClient(str(SESSION_FILE), api_id, api_hash,
                            device_model="Termux archive", system_version="Android",
                            app_version="1.0", connection_retries=10, retry_delay=3,
                            request_retries=8, flood_sleep_threshold=120)
    log("Подключаюсь к Telegram...")
    await client.start(
        phone=lambda: input("Номер телефона в формате +79991234567: ").strip(),
        code_callback=lambda: input("Код из Telegram (придёт в приложение): ").strip(),
        password=lambda: getpass.getpass("Облачный пароль Telegram (символы не видны — это нормально), Enter: "),
    )
    for p in SECRETS_DIR.glob("session*"):
        os.chmod(p, 0o600)
    try:
        me = await client.get_me()
        log(f"Вход выполнен: {display_name(me)}")
        chat = None if args.pick else archive.load_chat()
        if chat:
            entity = await resolve_saved_entity(client, chat)
        else:
            if archive.records:
                raise SystemExit("В папке архива уже есть сообщения. Для другого диалога укажите "
                                 "другую папку: --archive ~/archive2")
            entity = await pick_dialog(client)
            chat = {"peer_id": entity.id, "name": display_name(entity),
                    "username": getattr(entity, "username", None), "me": display_name(me)}
            archive.save_chat(chat)
        log(f"Диалог: {chat['name']}")
        names = {me.id: display_name(me), entity.id: display_name(entity)}

        head = await with_retries("подсчёт сообщений", lambda: client.get_messages(entity, limit=0))
        server_total = getattr(head, "total", None)
        log(f"Сервер сообщает: всего сообщений в диалоге {server_total}.")

        new_ids_before = set(archive.records)
        await export_messages(client, entity, archive, names, limit=args.limit)
        only = (set(archive.records) - new_ids_before) if args.limit else None

        max_bytes = int(args.max_mb * 1_000_000)
        _, failed = await download_media(client, entity, archive, args.media, max_bytes, only_ids=only)
        write_txt(archive)
        manifest, ok, missing = build_manifest(archive, chat, server_total, args.media, max_bytes, failed)
        print_report(manifest, ok, missing, test_mode=bool(args.limit))
        log(f"Архив: {archive.root}")
    finally:
        await client.disconnect()


def main():
    ap = argparse.ArgumentParser(description="Экспорт личного диалога Telegram")
    ap.add_argument("command", nargs="?", default="export", choices=["export", "pack"])
    ap.add_argument("--limit", type=int, help="пробный запуск: скачать только N новых сообщений")
    ap.add_argument("--media", default="all", choices=["all", "photos", "none"],
                    help="какие медиа скачивать (по умолчанию все)")
    ap.add_argument("--max-mb", type=float, default=50,
                    help="не скачивать видео/файлы больше N МБ (фото — всегда; по умолчанию 50)")
    ap.add_argument("--pick", action="store_true", help="выбрать диалог заново")
    ap.add_argument("--archive", default=str(DEFAULT_ARCHIVE), help="папка архива")
    args = ap.parse_args()
    if args.command == "pack":
        pack(Path(args.archive).expanduser())
        return
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        log("\nОстановлено. Всё скачанное сохранено; повторный запуск продолжит с этого места.")
        sys.exit(130)


if __name__ == "__main__":
    main()
