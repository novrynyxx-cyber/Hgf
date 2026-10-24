// Публикация с телефона (Termux): проверка, коммит и отправка на GitHub.
// Сам сайт собирает и выкладывает GitHub Actions (.github/workflows/publish.yml).
import { execFileSync } from "node:child_process";
import { ROOT, loadConfig, loadManifest, pageUrl } from "./lib.mjs";

const git = (...args) => execFileSync("git", args, { cwd: ROOT, encoding: "utf8" }).trim();
const run = (script) => execFileSync("node", [`scripts/${script}`], { cwd: ROOT, stdio: "inherit" });

run("build.mjs");
run("verify.mjs");

git("add", "--", "public", "data", "qr-codes", "inbox", "site.config.json");
const staged = git("diff", "--cached", "--name-only");
if (staged) {
  git("commit", "-m", "Обновление фотографий");
  console.log("Коммит создан.");
} else {
  console.log("Новых изменений нет.");
}

const branch = git("rev-parse", "--abbrev-ref", "HEAD");
execFileSync("git", ["push", "origin", branch], { cwd: ROOT, stdio: "inherit" });

const cfg = loadConfig();
console.log("\nОтправлено. GitHub Actions опубликует сайт за 1–3 минуты:");
console.log("  https://github.com/novrynyxx-cyber/Hgf/actions");
if (branch !== "main") console.log(`  Внимание: вы на ветке ${branch}; сайт публикуется только из main.`);
for (const p of loadManifest()) console.log(`  ${p.id}: ${pageUrl(cfg, p.id)}`);
