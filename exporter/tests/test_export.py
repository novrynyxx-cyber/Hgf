"""Офлайн-тест экспорта: имитация Telegram-клиента на настоящих объектах Telethon."""
import asyncio
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tg_export as tx  # noqa: E402
from telethon.tl import types  # noqa: E402

ME, FRIEND = 1, 2


def make_msg(i):
    date = datetime(2016, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i)
    out = i % 2 == 0
    media = None
    if i % 10 == 3:
        media = types.MessageMediaPhoto(photo=types.Photo(
            id=i, access_hash=0, file_reference=b"", date=date, dc_id=2,
            sizes=[types.PhotoSize(type="x", w=10, h=10, size=1234)]))
    elif i % 10 == 7:
        media = types.MessageMediaDocument(document=types.Document(
            id=i, access_hash=0, file_reference=b"", date=date, mime_type="audio/ogg",
            size=5000 if i != 17 else 10**9, dc_id=2, attributes=[
                types.DocumentAttributeAudio(duration=3, voice=True)]))
    m = types.Message(id=i, peer_id=types.PeerUser(FRIEND), date=date,
                      message=f"сообщение {i}", out=out,
                      from_id=types.PeerUser(ME if out else FRIEND), media=media,
                      reply_to=types.MessageReplyHeader(reply_to_msg_id=i - 1) if i % 5 == 0 else None)
    return m


class FakeClient:
    def __init__(self, n, fail_at=None):
        self.msgs = [make_msg(i) for i in range(1, n + 1)]
        self.fail_at = fail_at
        self.downloads = 0

    def is_connected(self):
        return True

    async def connect(self):
        pass

    async def iter_messages(self, entity, reverse, offset_id, limit, wait_time):
        count = 0
        for m in self.msgs:
            if m.id <= offset_id:
                continue
            if limit is not None and count >= limit:
                return
            if self.fail_at and m.id == self.fail_at:
                self.fail_at = None
                raise ConnectionError("сеть пропала")
            count += 1
            yield m

    async def get_messages(self, entity, ids=None, limit=None):
        return [next((m for m in self.msgs if m.id == i), None) for i in ids]

    async def download_media(self, msg, file):
        self.downloads += 1
        file.write(b"data")


async def scenario(root):
    arc = tx.Archive(root)
    names = {ME: "Я", FRIEND: "Друг"}
    c = FakeClient(250, fail_at=120)
    tx.asyncio.sleep = _nosleep

    # 1) пробный запуск на 50
    before = set(arc.records)
    await tx.export_messages(c, None, arc, names, limit=50)
    assert len(arc.records) == 50, len(arc.records)
    await tx.download_media(c, None, arc, "all", 50_000_000, only_ids=set(arc.records) - before)
    assert c.downloads == 9, c.downloads  # 5 фото + 5 голосовых среди 1..50, id 17 больше лимита

    # 2) полный запуск с обрывом сети на 120 — должен продолжить
    await tx.export_messages(c, None, arc, names)
    assert len(arc.records) == 250
    _, failed = await tx.download_media(c, None, arc, "all", 50_000_000)
    assert c.downloads == 49, c.downloads  # 50 медиа, одно (id 17) > лимита
    assert not failed

    # 3) повторный запуск: ни дублей, ни повторных скачиваний
    await tx.export_messages(c, None, arc, names)
    await tx.download_media(c, None, arc, "all", 50_000_000)
    assert c.downloads == 49
    lines = (root / "messages.jsonl").read_text().splitlines()
    assert len(lines) == 250 and len({json.loads(l)["id"] for l in lines}) == 250

    # 4) обрыв записи посреди строки -> восстановление
    with (root / "messages.jsonl").open("a") as f:
        f.write('{"id": 251, "te')
    arc2 = tx.Archive(root)
    assert len(arc2.records) == 250
    c.msgs.append(make_msg(251))
    await tx.export_messages(c, None, arc2, names)
    assert len(arc2.records) == 251

    tx.write_txt(arc2)
    manifest, ok, missing = tx.build_manifest(arc2, {"name": "Друг"}, 251, "all", 50_000_000, [])
    assert ok and missing == 0, manifest
    assert manifest["медиа"]["voice"]["не_нужно_по_настройкам"] == 1
    r3 = arc2.records[3]
    assert r3["media"]["path"] == "media/photos/3.jpg" and r3["sender"] == "Друг"
    assert arc2.records[7]["media"]["path"] == "media/voice/7.oga" or \
        arc2.records[7]["media"]["path"].startswith("media/voice/7.")
    assert arc2.records[10]["reply_to"] == 9 and arc2.records[10]["sender"] == "Я"
    txt = (root / "messages.txt").read_text()
    assert "#3 [" in txt and "photo: media/photos/3.jpg" in txt
    tx.print_report(manifest, ok, missing, test_mode=False)


_real_sleep = asyncio.sleep


async def _nosleep(s):
    await _real_sleep(0)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(scenario(Path(d) / "arc"))
    print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
