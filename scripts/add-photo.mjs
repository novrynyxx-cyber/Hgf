// Добавление фотографий: каждая получает новый номер, страницу и QR-код.
//
//   npm run add -- путь/к/фото.jpg [ещё.jpg ...] [--title "Подпись"]
//   npm run inbox           — обработать все файлы из папки inbox/
//
// Существующие фотографии и QR-коды никогда не перезаписываются.
import fs from "node:fs";
import path from "node:path";
import { Jimp } from "jimp";
import {
  IMAGES_DIR, INBOX_DIR, imageFiles, loadConfig, loadManifest, nextId,
  pageUrl, qrFiles, rel, saveManifest,
} from "./lib.mjs";
import { generateQr } from "./qr.mjs";

const SUPPORTED = new Set([".jpg", ".jpeg", ".png"]);
const FULL_PX = 2400;
const SMALL_PX = 1080;

function parseArgs(argv) {
  const out = { files: [], title: null, inbox: false };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--inbox") out.inbox = true;
    else if (argv[i] === "--title") out.title = argv[++i];
    else out.files.push(argv[i]);
  }
  if (out.inbox) {
    out.files = fs.existsSync(INBOX_DIR)
      ? fs.readdirSync(INBOX_DIR)
          .filter((f) => !f.startsWith(".") && f.toLowerCase() !== "readme.md")
          .sort()
          .map((f) => path.join(INBOX_DIR, f))
      : [];
  }
  return out;
}

// Уменьшает до maxPx по длинной стороне. Jimp сам поворачивает кадр по EXIF,
// а при сохранении в JPEG метаданные (в т.ч. GPS-координаты) не записываются.
async function resizedJpeg(src, maxPx, quality) {
  const img = await Jimp.read(src);
  if (Math.max(img.bitmap.width, img.bitmap.height) > maxPx) {
    img.scaleToFit({ w: maxPx, h: maxPx });
  }
  const buffer = await img.getBuffer("image/jpeg", { quality });
  return { buffer, width: img.bitmap.width, height: img.bitmap.height };
}

function writeNew(file, data) {
  // Флаг "wx" — ошибка, если файл уже существует: ничего не перезаписываем.
  fs.writeFileSync(file, data, { flag: "wx" });
}

async function addPhoto(src, title, cfg, photos) {
  const ext = path.extname(src).toLowerCase();
  if (!SUPPORTED.has(ext)) {
    throw new Error(`${src}: формат ${ext || "(без расширения)"} не поддерживается — нужен JPG или PNG`);
  }
  const id = nextId(photos);
  const names = imageFiles(id);
  const qr = qrFiles(id);
  for (const f of [path.join(IMAGES_DIR, names.full), path.join(IMAGES_DIR, names.small), qr.png, qr.pdf]) {
    if (fs.existsSync(f)) throw new Error(`${rel(f)} уже существует — остановлено, чтобы ничего не перезаписать`);
  }

  console.log(`→ ${path.basename(src)} → ${id}`);
  const full = await resizedJpeg(src, FULL_PX, 86);
  const small = await resizedJpeg(src, SMALL_PX, 80);
  fs.mkdirSync(IMAGES_DIR, { recursive: true });
  writeNew(path.join(IMAGES_DIR, names.full), full.buffer);
  writeNew(path.join(IMAGES_DIR, names.small), small.buffer);

  const url = pageUrl(cfg, id);
  await generateQr(id, url);

  const entry = {
    id,
    title: title || `Фото ${id.split("-")[1]}`,
    width: full.width,
    height: full.height,
    smallWidth: small.width,
    smallHeight: small.height,
    addedAt: new Date().toISOString(),
    url,
  };
  photos.push(entry);
  saveManifest(photos);

  console.log(`  страница: ${url}`);
  console.log(`  QR PNG:   ${rel(qr.png)}`);
  console.log(`  QR PDF:   ${rel(qr.pdf)}`);
  return entry;
}

const args = parseArgs(process.argv.slice(2));
if (!args.files.length) {
  if (args.inbox) {
    console.log("inbox/ пуста — новых фотографий нет.");
    process.exit(0);
  }
  console.error('Использование: npm run add -- фото.jpg [--title "Подпись"]');
  process.exit(1);
}

const cfg = loadConfig();
const photos = loadManifest();
let failed = 0;
for (const src of args.files) {
  try {
    await addPhoto(src, args.title, cfg, photos);
    // Из inbox/ файл убирается только после успешной обработки:
    // обработанная копия уже лежит в public/images/.
    if (args.inbox) fs.unlinkSync(src);
  } catch (err) {
    failed++;
    console.error(`✗ ${err.message}`);
  }
}
if (failed) process.exit(1);
