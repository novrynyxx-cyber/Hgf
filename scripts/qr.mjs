// Генерация QR-кода: PNG высокого разрешения и векторный PDF формата A4.
import fs from "node:fs";
import QRCode from "qrcode";
import { PDFDocument, StandardFonts, rgb } from "pdf-lib";
import { QR_DIR, qrFiles } from "./lib.mjs";

const MARGIN_MODULES = 4; // «тихая зона» по стандарту QR
const PNG_TARGET_PX = 2400;
const MM = 72 / 25.4;

export async function generateQr(id, url) {
  fs.mkdirSync(QR_DIR, { recursive: true });
  const files = qrFiles(id);
  // Уровень коррекции Q (~25%) — код читается даже с потёртостями после печати.
  const qr = QRCode.create(url, { errorCorrectionLevel: "Q" });
  const size = qr.modules.size;

  // Целое число пикселей на модуль — края модулей идеально чёткие.
  const scale = Math.ceil(PNG_TARGET_PX / (size + MARGIN_MODULES * 2));
  await QRCode.toFile(files.png, url, {
    errorCorrectionLevel: "Q",
    margin: MARGIN_MODULES,
    scale,
    color: { dark: "#000000", light: "#ffffff" },
  });

  await writePdf(files.pdf, qr.modules, id, url);
  return files;
}

async function writePdf(file, modules, id, url) {
  const doc = await PDFDocument.create();
  doc.setTitle(`QR ${id}`);
  doc.setSubject(url);
  const page = doc.addPage([210 * MM, 297 * MM]);
  const { width: W, height: H } = page.getSize();
  page.drawRectangle({ x: 0, y: 0, width: W, height: H, color: rgb(1, 1, 1) });

  // QR 150 × 150 мм вместе с белыми полями, по центру листа.
  const total = modules.size + MARGIN_MODULES * 2;
  const side = 150 * MM;
  const cell = side / total;
  const x0 = (W - side) / 2;
  const y0 = (H - side) / 2 + 10 * MM;
  for (let r = 0; r < modules.size; r++) {
    for (let c = 0; c < modules.size; c++) {
      if (!modules.get(r, c)) continue;
      // Небольшой нахлёст убирает просветы между соседними модулями при печати.
      page.drawRectangle({
        x: x0 + (c + MARGIN_MODULES) * cell,
        y: y0 + side - (r + MARGIN_MODULES + 1) * cell,
        width: cell + 0.05,
        height: cell + 0.05,
        color: rgb(0, 0, 0),
      });
    }
  }

  const font = await doc.embedFont(StandardFonts.Helvetica);
  const bold = await doc.embedFont(StandardFonts.HelveticaBold);
  const title = id.toUpperCase();
  page.drawText(title, {
    x: (W - bold.widthOfTextAtSize(title, 20)) / 2,
    y: y0 + side + 8 * MM,
    size: 20,
    font: bold,
    color: rgb(0, 0, 0),
  });
  page.drawText(url, {
    x: (W - font.widthOfTextAtSize(url, 11)) / 2,
    y: y0 - 8 * MM,
    size: 11,
    font,
    color: rgb(0.25, 0.25, 0.25),
  });

  fs.writeFileSync(file, await doc.save());
}
