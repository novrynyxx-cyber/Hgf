// Проверка перед публикацией: каждый QR-код распознаётся и ведёт ровно
// на страницу своей фотографии, все файлы на месте.
import fs from "node:fs";
import path from "node:path";
import { PNG } from "pngjs";
import jsQR from "jsqr";
import {
  DIST_DIR, IMAGES_DIR, imageFiles, loadConfig, loadManifest, pagePath, pageUrl, qrFiles, rel,
} from "./lib.mjs";

const cfg = loadConfig();
const photos = loadManifest();
const errors = [];

for (const p of photos) {
  const expected = pageUrl(cfg, p.id);
  if (p.url && p.url !== expected) {
    errors.push(`${p.id}: в манифесте ${p.url}, а по конфигу ${expected} — старый QR-код перестал бы работать`);
  }
  for (const f of Object.values(imageFiles(p.id))) {
    if (!fs.existsSync(path.join(IMAGES_DIR, f))) errors.push(`${p.id}: нет файла public/images/${f}`);
  }
  const qr = qrFiles(p.id);
  if (!fs.existsSync(qr.pdf)) errors.push(`${p.id}: нет ${rel(qr.pdf)}`);
  if (!fs.existsSync(qr.png)) {
    errors.push(`${p.id}: нет ${rel(qr.png)}`);
    continue;
  }
  const png = PNG.sync.read(fs.readFileSync(qr.png));
  const decoded = jsQR(new Uint8ClampedArray(png.data), png.width, png.height);
  if (!decoded) errors.push(`${p.id}: QR-код не распознаётся`);
  else if (decoded.data !== expected) errors.push(`${p.id}: QR ведёт на ${decoded.data}, ожидалось ${expected}`);
  else console.log(`✓ ${p.id}: QR ${png.width}×${png.height}px → ${decoded.data}`);

  if (fs.existsSync(DIST_DIR) && !fs.existsSync(path.join(DIST_DIR, pagePath(p.id), "index.html"))) {
    errors.push(`${p.id}: страница не собрана (запустите npm run build)`);
  }
}

if (errors.length) {
  for (const e of errors) console.error(`✗ ${e}`);
  process.exit(1);
}
console.log(`Проверено фото: ${photos.length}`);
