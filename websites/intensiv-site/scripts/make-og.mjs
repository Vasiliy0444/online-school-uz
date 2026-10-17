// Картинка превью для соцсетей и мессенджеров: public/og.png, 1200×630. Тексты — согласованные (блок 1).
// Запуск: npm run og
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import puppeteer from 'puppeteer-core';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const CHROME = process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const font = (pkg, file) => pathToFileURL(resolve(root, 'node_modules/@fontsource', pkg, 'files', file)).href;

const html = `<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>
@font-face { font-family: 'Inter Tight'; font-weight: 900; src: url('${font('inter-tight', 'inter-tight-cyrillic-900-normal.woff2')}') format('woff2'); unicode-range: U+0400-045F; }
@font-face { font-family: 'Inter Tight'; font-weight: 900; src: url('${font('inter-tight', 'inter-tight-latin-900-normal.woff2')}') format('woff2'); }
@font-face { font-family: 'Inter'; font-weight: 600; src: url('${font('inter', 'inter-cyrillic-600-normal.woff2')}') format('woff2'); unicode-range: U+0400-045F; }
@font-face { font-family: 'Inter'; font-weight: 600; src: url('${font('inter', 'inter-latin-600-normal.woff2')}') format('woff2'); }
* { box-sizing: border-box; margin: 0; }
body { width: 1200px; height: 630px; background: #87ea5c; color: #083400; font-family: 'Inter', sans-serif; padding: 56px 64px; display: flex; flex-direction: column; justify-content: space-between; }
.top { display: flex; justify-content: space-between; align-items: center; }
.logo { font-family: 'Inter Tight'; font-weight: 900; font-size: 34px; letter-spacing: -0.03em; }
.pills { display: flex; gap: 12px; }
.pill { height: 48px; padding: 0 22px; border-radius: 9999px; border: 3px solid #083400; font-weight: 600; font-size: 22px; display: flex; align-items: center; }
.pill.solid { background: #083400; color: #87ea5c; }
h1 { font-family: 'Inter Tight'; font-weight: 900; font-size: 84px; line-height: .92; letter-spacing: -0.045em; max-width: 1060px; text-wrap: balance; }
.money { display: inline-block; background: #fff; border-radius: 9999px; padding: 0 .16em; transform: rotate(-2deg); }
</style></head><body>
<div class="top"><div class="logo">ИИ на заказ</div><div class="pills"><span class="pill">Бесплатный интенсив в Telegram</span><span class="pill solid">3 урока</span></div></div>
<h1>Как заработать на&nbsp;ИИ в&nbsp;2026&nbsp;году и&nbsp;выйти на&nbsp;стабильные <span class="money">$1000</span> в&nbsp;месяц</h1>
</body></html>`;

const dir = mkdtempSync(join(tmpdir(), 'og-'));
const file = join(dir, 'og.html');
writeFileSync(file, html);

const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--allow-file-access-from-files'] });
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 630, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(file).href, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  const out = resolve(root, 'public/og.png');
  await page.screenshot({ path: out, type: 'png' });
  console.log(`og: ${out}`);
} finally {
  await browser.close();
}
