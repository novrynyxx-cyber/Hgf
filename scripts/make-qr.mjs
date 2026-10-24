// Повторная генерация QR-кодов для уже добавленных фото.
//
//   npm run qr -- photo-001 [photo-002 ...]
//   npm run qr -- --missing   — создать только отсутствующие QR-файлы
//
// Старые QR-коды не трогаются, если файл уже есть: удалите его сами,
// если действительно хотите пересоздать.
import fs from "node:fs";
import { loadConfig, loadManifest, pageUrl, qrFiles, rel } from "./lib.mjs";
import { generateQr } from "./qr.mjs";

const cfg = loadConfig();
const photos = loadManifest();
const argv = process.argv.slice(2);
const ids = argv.includes("--missing") ? photos.map((p) => p.id) : argv;
if (!ids.length) {
  console.error("Использование: npm run qr -- photo-001 | --missing");
  process.exit(1);
}

let failed = 0;
for (const id of ids) {
  if (!photos.some((p) => p.id === id)) {
    console.error(`✗ ${id}: нет такой фотографии`);
    failed++;
    continue;
  }
  const files = qrFiles(id);
  if (fs.existsSync(files.png) || fs.existsSync(files.pdf)) {
    if (!argv.includes("--missing")) console.log(`= ${id}: QR уже есть (${rel(files.png)}), пропущено`);
    continue;
  }
  await generateQr(id, pageUrl(cfg, id));
  console.log(`✓ ${id}: ${rel(files.png)}, ${rel(files.pdf)}`);
}
if (failed) process.exit(1);
