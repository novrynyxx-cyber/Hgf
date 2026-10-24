// Проверка опубликованного сайта по публичным ссылкам (запускается в GitHub Actions
// после деплоя). Ждёт, пока CDN GitHub Pages отдаст свежую версию.
import { imageFiles, loadConfig, loadManifest, pageUrl } from "./lib.mjs";

const cfg = loadConfig();
const photos = loadManifest();
const deployedUrl = process.argv[2];

if (deployedUrl) {
  const norm = (u) => new URL(u.endsWith("/") ? u : u + "/").href.toLowerCase();
  if (norm(deployedUrl) !== norm(cfg.baseUrl)) {
    console.error(`✗ GitHub Pages опубликовал сайт по адресу ${deployedUrl}, а в site.config.json указан ${cfg.baseUrl}`);
    process.exit(1);
  }
  console.log(`✓ Адрес сайта совпадает с конфигом: ${cfg.baseUrl}`);
}

async function check(url, mustContain) {
  for (let attempt = 1; attempt <= 20; attempt++) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      const body = mustContain ? await res.text() : null;
      if (res.ok && (!mustContain || body.includes(mustContain))) return res.status;
    } catch {}
    await new Promise((r) => setTimeout(r, 6000));
  }
  throw new Error(`${url} недоступен`);
}

let failed = 0;
const targets = [[cfg.baseUrl, null]];
for (const p of photos) {
  const img = imageFiles(p.id);
  targets.push([pageUrl(cfg, p.id), `images/${img.full}`]);
  targets.push([new URL(`images/${img.full}`, cfg.baseUrl).href, null]);
  targets.push([new URL(`qr/${p.id}.png`, cfg.baseUrl).href, null]);
  targets.push([new URL(`qr/${p.id}.pdf`, cfg.baseUrl).href, null]);
}
for (const [url, needle] of targets) {
  try {
    const status = await check(url, needle);
    console.log(`✓ ${status} ${url}`);
  } catch (err) {
    failed++;
    console.error(`✗ ${err.message}`);
  }
}
process.exit(failed ? 1 : 0);
