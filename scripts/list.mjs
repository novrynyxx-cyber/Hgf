// Список опубликованных фото со ссылками и путями к QR-файлам.
import { loadConfig, loadManifest, pageUrl, qrFiles, rel } from "./lib.mjs";

const cfg = loadConfig();
const photos = loadManifest();
if (!photos.length) console.log("Фотографий пока нет.");
for (const p of photos) {
  const qr = qrFiles(p.id);
  console.log(`${p.id}  ${p.title}`);
  console.log(`  страница: ${pageUrl(cfg, p.id)}`);
  console.log(`  QR PNG:   ${rel(qr.png)}  (онлайн: ${new URL(`qr/${p.id}.png`, cfg.baseUrl).href})`);
  console.log(`  QR PDF:   ${rel(qr.pdf)}  (онлайн: ${new URL(`qr/${p.id}.pdf`, cfg.baseUrl).href})`);
}
