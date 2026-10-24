# Фото + QR-код для печати

Каждая фотография получает постоянную страницу на GitHub Pages и QR-код (PNG и PDF A4).

- Сайт: https://novrynyxx-cyber.github.io/Hgf/
- Страница фото: `https://novrynyxx-cyber.github.io/Hgf/p/photo-NNN/`
- QR-коды: `qr-codes/photo-NNN.png` (2430×2430 px) и `qr-codes/photo-NNN.pdf` (A4, вектор, 15 × 15 см)
- Те же QR онлайн (удобно скачать на телефон): `https://novrynyxx-cyber.github.io/Hgf/qr/photo-NNN.png` и `.pdf`

## Добавить фото — способ 1: только телефон, без Termux

1. Откройте https://github.com/novrynyxx-cyber/Hgf/tree/main/inbox
   (в браузере, режим «Версия для ПК» удобнее).
2. **Add file → Upload files**, выберите фото (JPG/PNG), нажмите **Commit changes**.
3. Через 1–3 минуты откройте вкладку **Actions** — зелёная галочка «Publish site» значит,
   что сайт опубликован и ссылки проверены.
4. Новые файлы появятся в `qr-codes/` (например, `photo-002.png` / `.pdf`),
   ссылка — в `data/photos.json`.

## Добавить фото — способ 2: Termux

```sh
git pull
npm install                                    # один раз
npm run add -- ~/storage/shared/DCIM/Camera/IMG_1234.jpg --title "Подпись"
npm run publish-site                           # проверка + коммит + push в GitHub
```

`npm run list` — все фото со ссылками и путями к QR-файлам.
(Для доступа к галерее в Termux один раз выполните `termux-setup-storage`.)

## Заменить фотографию

Старые ссылки и QR-коды специально не перезаписываются: добавьте новое фото — оно получит
новый номер и новый QR. Если нужно, чтобы **старый** QR показывал другой снимок,
замените оба файла `public/images/photo-NNN.jpg` и `public/images/photo-NNN-1080.jpg`
(сделайте это осознанно — это перезапись) и опубликуйте снова.

## Повторная публикация

Любой push в `main` пересобирает и публикует сайт. Вручную:
**Actions → Publish site → Run workflow**. Из Termux: `npm run publish-site`.

## Команды

| Команда | Что делает |
| --- | --- |
| `npm run add -- фото.jpg [--title "…"]` | добавить фото, создать страницу и QR |
| `npm run inbox` | обработать все файлы из `inbox/` |
| `npm run qr -- --missing` | создать отсутствующие QR-файлы |
| `npm run build` | собрать сайт в `dist/` |
| `npm run verify` | проверить, что каждый QR распознаётся и ведёт на свою страницу |
| `npm run list` | показать все ссылки |
| `npm run publish-site` | build + verify + commit + push |

## Устройство

```
inbox/               сюда кладутся новые фото (обрабатываются автоматически)
public/images/       опубликованные фото: photo-NNN.jpg (до 2400 px) и photo-NNN-1080.jpg
qr-codes/            QR для печати: photo-NNN.png и photo-NNN.pdf
data/photos.json     список фото (номер, подпись, размеры, ссылка)
scripts/             добавление, QR, сборка, проверки
site.config.json     публичный адрес сайта (baseUrl)
.github/workflows/   публикация на GitHub Pages
```

Фото уменьшаются и сохраняются без EXIF-метаданных (GPS, модель телефона).
Учтите: всё в этом репозитории и на сайте публично, а файл, загруженный в `inbox/`,
остаётся в истории git.
