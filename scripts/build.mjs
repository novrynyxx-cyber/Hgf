// Сборка статического сайта в dist/ (именно эта папка публикуется на GitHub Pages).
import fs from "node:fs";
import path from "node:path";
import {
  DIST_DIR, IMAGES_DIR, QR_DIR, imageFiles, loadConfig, loadManifest, pagePath, qrFiles,
} from "./lib.mjs";

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const BASE_CSS = `*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
html,body{margin:0;background:#0e0e10;color:#e8e8ea;font:16px/1.4 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}`;

function head({ title, description, ogImage, url, extraCss, preload }) {
  return `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>${esc(title)}</title>
<meta name="description" content="${esc(description)}">
<meta name="theme-color" content="#0e0e10">
<meta name="color-scheme" content="dark">
<meta name="format-detection" content="telephone=no">
${url ? `<link rel="canonical" href="${esc(url)}">\n<meta property="og:url" content="${esc(url)}">` : ""}
<meta property="og:type" content="website">
<meta property="og:title" content="${esc(title)}">
${ogImage ? `<meta property="og:image" content="${esc(ogImage)}">\n<meta name="twitter:card" content="summary_large_image">` : ""}
${preload || ""}
<style>
${BASE_CSS}
${extraCss}
</style>
</head>`;
}

function photoPage(cfg, p) {
  const img = imageFiles(p.id);
  const url = new URL(pagePath(p.id), cfg.baseUrl).href;
  const srcset = `../../images/${img.small} ${p.smallWidth}w, ../../images/${img.full} ${p.width}w`;
  // Фото занимает весь экран и вписывается целиком, сохраняя пропорции.
  // 100dvh учитывает прячущуюся адресную строку на iPhone и Android,
  // safe-area — вырезы и закругления экрана.
  const css = `html,body{height:100%;overflow:hidden}
main{display:grid;place-items:center;width:100vw;height:100vh;height:100dvh;
padding:env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)}
img{display:block;width:auto;height:auto;max-width:100%;
max-height:calc(100vh - env(safe-area-inset-top) - env(safe-area-inset-bottom));
max-height:calc(100dvh - env(safe-area-inset-top) - env(safe-area-inset-bottom));
-webkit-user-select:none;user-select:none}`;
  const preload = `<link rel="preload" as="image" href="../../images/${img.full}" imagesrcset="${srcset}" imagesizes="100vw" fetchpriority="high">`;
  return `${head({
    title: p.title,
    description: p.title,
    ogImage: new URL(`images/${img.small}`, cfg.baseUrl).href,
    url,
    extraCss: css,
    preload,
  })}
<body>
<main>
<img src="../../images/${img.full}" srcset="${srcset}" sizes="100vw"
 width="${p.width}" height="${p.height}" alt="${esc(p.title)}" fetchpriority="high" decoding="async">
</main>
</body>
</html>
`;
}

function indexPage(cfg, photos) {
  const css = `main{max-width:1100px;margin:0 auto;padding:calc(24px + env(safe-area-inset-top)) max(16px,env(safe-area-inset-right)) calc(32px + env(safe-area-inset-bottom)) max(16px,env(safe-area-inset-left))}
h1{font-size:20px;font-weight:600;margin:0 0 16px}
ul{list-style:none;margin:0;padding:0;display:grid;gap:8px;grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
a{display:block;aspect-ratio:1;overflow:hidden;border-radius:8px;background:#1a1a1d}
a img{width:100%;height:100%;object-fit:cover;display:block}
p{color:#9a9aa0}`;
  const items = [...photos].reverse().map((p) => {
    const img = imageFiles(p.id);
    return `<li><a href="${pagePath(p.id)}"><img src="images/${img.small}" width="${p.smallWidth}" height="${p.smallHeight}" alt="${esc(p.title)}" loading="lazy" decoding="async"></a></li>`;
  });
  return `${head({ title: cfg.siteTitle, description: cfg.siteTitle, url: cfg.baseUrl, extraCss: css })}
<body>
<main>
<h1>${esc(cfg.siteTitle)}</h1>
${items.length ? `<ul>\n${items.join("\n")}\n</ul>` : "<p>Фотографий пока нет.</p>"}
</main>
</body>
</html>
`;
}

function notFoundPage(cfg) {
  const css = `main{min-height:100vh;min-height:100dvh;display:grid;place-items:center;text-align:center;padding:16px}
a{color:#e8e8ea}`;
  return `${head({ title: "Страница не найдена", description: "404", extraCss: css })}
<body><main><div><p>Страница не найдена</p><p><a href="${esc(cfg.baseUrl)}">На главную</a></p></div></main></body>
</html>
`;
}

const cfg = loadConfig();
const photos = loadManifest();

fs.rmSync(DIST_DIR, { recursive: true, force: true });
fs.mkdirSync(path.join(DIST_DIR, "images"), { recursive: true });
fs.mkdirSync(path.join(DIST_DIR, "qr"), { recursive: true });

for (const p of photos) {
  const img = imageFiles(p.id);
  for (const f of [img.full, img.small]) {
    fs.copyFileSync(path.join(IMAGES_DIR, f), path.join(DIST_DIR, "images", f));
  }
  const qr = qrFiles(p.id);
  for (const f of [qr.png, qr.pdf]) {
    if (fs.existsSync(f)) fs.copyFileSync(f, path.join(DIST_DIR, "qr", path.basename(f)));
  }
  const dir = path.join(DIST_DIR, pagePath(p.id));
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "index.html"), photoPage(cfg, p));
}
fs.writeFileSync(path.join(DIST_DIR, "index.html"), indexPage(cfg, photos));
fs.writeFileSync(path.join(DIST_DIR, "404.html"), notFoundPage(cfg));
fs.writeFileSync(path.join(DIST_DIR, ".nojekyll"), "");
fs.writeFileSync(
  path.join(DIST_DIR, "urls.txt"),
  [cfg.baseUrl, ...photos.map((p) => new URL(pagePath(p.id), cfg.baseUrl).href)].join("\n") + "\n",
);
console.log(`Собрано: ${photos.length} фото → dist/`);
