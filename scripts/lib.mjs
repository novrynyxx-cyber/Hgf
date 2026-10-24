// Общие пути, конфиг и манифест фотографий.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const IMAGES_DIR = path.join(ROOT, "public", "images");
export const QR_DIR = path.join(ROOT, "qr-codes");
export const INBOX_DIR = path.join(ROOT, "inbox");
export const DIST_DIR = path.join(ROOT, "dist");
export const MANIFEST = path.join(ROOT, "data", "photos.json");

export function loadConfig() {
  const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, "site.config.json"), "utf8"));
  const url = new URL(cfg.baseUrl);
  if (url.protocol !== "https:") throw new Error("baseUrl должен начинаться с https://");
  if (["localhost", "127.0.0.1"].includes(url.hostname)) throw new Error("baseUrl не может быть локальным адресом");
  if (!url.pathname.endsWith("/")) url.pathname += "/";
  return { ...cfg, baseUrl: url.href };
}

export function loadManifest() {
  if (!fs.existsSync(MANIFEST)) return [];
  return JSON.parse(fs.readFileSync(MANIFEST, "utf8"));
}

export function saveManifest(photos) {
  fs.mkdirSync(path.dirname(MANIFEST), { recursive: true });
  fs.writeFileSync(MANIFEST, JSON.stringify(photos, null, 2) + "\n");
}

export function nextId(photos) {
  const max = photos.reduce((m, p) => Math.max(m, Number(p.id.split("-")[1])), 0);
  return `photo-${String(max + 1).padStart(3, "0")}`;
}

export function pagePath(id) {
  return `p/${id}/`;
}

export function pageUrl(cfg, id) {
  return new URL(pagePath(id), cfg.baseUrl).href;
}

export function imageFiles(id) {
  return { full: `${id}.jpg`, small: `${id}-1080.jpg` };
}

export function qrFiles(id) {
  return { png: path.join(QR_DIR, `${id}.png`), pdf: path.join(QR_DIR, `${id}.pdf`) };
}

export function rel(p) {
  return path.relative(ROOT, p);
}
