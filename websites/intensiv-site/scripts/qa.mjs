// Автопроверка собранного сайта через установленный Chrome (puppeteer-core).
// Запуск: npm run preview (в другом окне), затем npm run qa -- [baseUrl] [outDir]
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import puppeteer from 'puppeteer-core';

const BASE = process.argv[2] ?? 'http://localhost:4174/ai-na-zakaz-intensiv/';
const OUT = resolve(process.argv[3] ?? 'qa-report');
const CHROME = process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const SETTLE_MS = 600;
const MIN_TAP = 44;
// Самый мелкий текст образца edgroup — надзаголовок 10 px на телефоне. Мельче — ошибка.
const MIN_FONT = 10;
const UTM_QUERY = '?utm_source=instagram&utm_campaign=sep_test&utm_content=hook_math_v2';
const EXPECTED_PAYLOAD = 've-instagram-sep_test-hook_math_v2';

const VIEWPORTS = [
  { name: '320x640', width: 320, height: 640, mobile: true },
  { name: '360x640', width: 360, height: 640, mobile: true },
  { name: '375x812', width: 375, height: 812, mobile: true },
  { name: '768x1024', width: 768, height: 1024, mobile: true },
  { name: '1024x768', width: 1024, height: 768, mobile: false },
  { name: '1440x900', width: 1440, height: 900, mobile: false },
  { name: '1920x1080', width: 1920, height: 1080, mobile: false },
];
const FOLD_VIEWPORTS = new Set(['320x640', '360x640', '375x812']);
const SHOT_VIEWPORTS = new Set(['375x812', '1440x900']);

mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function openPage(browser, url, vp) {
  const page = await browser.newPage();
  const problems = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error' || /Content Security Policy/i.test(msg.text())) problems.push(msg.text());
  });
  page.on('pageerror', (err) => problems.push(`pageerror: ${err.message}`));
  page.on('requestfailed', (req) => problems.push(`requestfailed: ${req.url()} ${req.failure()?.errorText ?? ''}`));
  await page.setViewport({ width: vp.width, height: vp.height, deviceScaleFactor: vp.mobile ? 2 : 1, isMobile: vp.mobile, hasTouch: vp.mobile });
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
  await page.evaluate(() => document.fonts.ready);
  await sleep(SETTLE_MS);
  return { page, problems };
}

async function measure(page) {
  return page.evaluate(
    ({ MIN_TAP, MIN_FONT }) => {
      const overflowX = document.documentElement.scrollWidth - window.innerWidth;
      const heroBtn = document.querySelector('.cta--hero .btn')?.getBoundingClientRect();
      const isDecor = (el) => el.closest('[aria-hidden="true"], .sticky-cta, .skip-link');

      const smallText = [];
      for (const el of document.querySelectorAll('body *')) {
        if (isDecor(el)) continue;
        const hasText = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
        if (!hasText) continue;
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden') continue;
        const size = parseFloat(cs.fontSize);
        if (size < MIN_FONT) smallText.push(`${el.tagName.toLowerCase()}.${el.className} ${size}px «${el.textContent.trim().slice(0, 30)}»`);
      }

      const smallTaps = [];
      for (const el of document.querySelectorAll('a, button, summary')) {
        if (isDecor(el)) continue;
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height) continue;
        if (r.height < MIN_TAP || r.width < MIN_TAP) smallTaps.push(`${el.tagName.toLowerCase()} «${el.textContent.trim().slice(0, 30)}» ${Math.round(r.width)}x${Math.round(r.height)}`);
      }

      const badCtas = [...document.querySelectorAll('[data-cta]')]
        .map((a) => a.getAttribute('href') ?? '')
        .filter((href) => !(href.startsWith('https://t.me/') || (href.startsWith('#') && href.length > 1 && document.querySelector(href))));

      return {
        badCtas,
        overflowX,
        heroCta: heroBtn ? { top: Math.round(heroBtn.top), bottom: Math.round(heroBtn.bottom) } : null,
        heroCtaInFold: heroBtn ? heroBtn.bottom <= window.innerHeight : false,
        smallText: [...new Set(smallText)].slice(0, 12),
        smallTaps: [...new Set(smallTaps)].slice(0, 12),
        emptySlots: document.querySelectorAll('.slot--empty').length,
        ab: window.__AB ?? null,
      };
    },
    { MIN_TAP, MIN_FONT },
  );
}

async function stickyCheck(page) {
  const before = await page.evaluate(() => document.querySelector('.sticky-cta')?.classList.contains('is-visible') ?? null);
  // Мгновенная прокрутка: плавная (scroll-behavior: smooth) не успевает за замером.
  await page.evaluate(() => {
    document.documentElement.style.scrollBehavior = 'auto';
    document.getElementById('hosts')?.scrollIntoView();
  });
  await sleep(900);
  const middle = await page.evaluate(() => document.querySelector('.sticky-cta')?.classList.contains('is-visible') ?? null);
  await page.evaluate(() => window.scrollTo(0, 0));
  await sleep(300);
  return { atTop: before, atHosts: middle };
}

async function screenshots(page, vp) {
  await page.screenshot({ path: `${OUT}/${vp.name}.png` });
  // Chrome не снимает больше 16384 px за раз: полную страницу телефона снимаем в масштабе 1
  if (vp.mobile) await page.setViewport({ width: vp.width, height: vp.height, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
  await page.evaluate(() => document.querySelector('.sticky-cta')?.remove());
  await page.screenshot({ path: `${OUT}/${vp.name}_full.png`, fullPage: true });
}

const report = { base: BASE, generatedAt: new Date().toISOString(), pages: [], noJs: null, utm: null };
const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--hide-scrollbars'] });

try {
  for (const vp of VIEWPORTS) {
    const { page, problems } = await openPage(browser, BASE, vp);
    const m = await measure(page);
    const sticky = vp.width < 960 ? await stickyCheck(page) : null;
    if (SHOT_VIEWPORTS.has(vp.name)) await screenshots(page, vp);
    report.pages.push({ viewport: vp.name, ...m, sticky, problems });
    await page.close();
  }

  // Без JavaScript: все блоки видны, кнопки ведут в бот или к существующему якорю.
  const noJsPage = await browser.newPage();
  await noJsPage.setJavaScriptEnabled(false);
  await noJsPage.setViewport({ width: 375, height: 812, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  await noJsPage.goto(BASE, { waitUntil: 'networkidle0' });
  report.noJs = await noJsPage.evaluate(() => {
    const hidden = [...document.querySelectorAll('main section, footer')].filter((el) => {
      const cs = getComputedStyle(el);
      return cs.visibility === 'hidden' || Number(cs.opacity) === 0 || cs.display === 'none';
    }).length;
    const hrefs = [...new Set([...document.querySelectorAll('[data-cta]')].map((a) => a.getAttribute('href')))];
    const broken = hrefs.filter((h) => !(h.startsWith('https://t.me/') || (h.startsWith('#') && document.querySelector(h))));
    return { hidden, hrefs, broken };
  });
  await noJsPage.close();

  // Метки рекламы и подмена заголовка под хук; метка сохраняется, если вернуться без UTM.
  const ctx = await browser.createBrowserContext();
  const page = await ctx.newPage();
  await page.goto(`${BASE}${UTM_QUERY}`, { waitUntil: 'networkidle0' });
  report.utm = await page.evaluate(() => ({
    ab: window.__AB,
    hook: document.getElementById('hero-title')?.dataset.hook ?? null,
    h1: document.getElementById('hero-title')?.textContent.replace(/\s+/g, ' ').trim(),
  }));
  await page.goto(BASE, { waitUntil: 'networkidle0' });
  report.utm.afterReturnWithoutUtm = await page.evaluate(() => window.__AB?.payload);
  await ctx.close();
} finally {
  await browser.close();
}

writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 2));

let failures = 0;
for (const p of report.pages) {
  const flags = [];
  if (p.overflowX > 0) flags.push(`горизонтальная прокрутка ${p.overflowX}px`);
  if (FOLD_VIEWPORTS.has(p.viewport) && !p.heroCtaInFold) flags.push(`кнопка ниже первого экрана (${p.heroCta?.bottom}px)`);
  if (p.smallText.length) flags.push(`мелкий текст: ${p.smallText.join('; ')}`);
  if (p.smallTaps.length) flags.push(`маленькие зоны нажатия: ${p.smallTaps.join('; ')}`);
  if (p.badCtas?.length) flags.push(`кнопки ведут в никуда: ${p.badCtas.join(', ')}`);
  if (p.problems.length) flags.push(`консоль: ${p.problems.join(' | ')}`);
  if (p.sticky && (p.sticky.atTop !== false || p.sticky.atHosts !== true)) flags.push(`липкая кнопка: ${JSON.stringify(p.sticky)}`);
  if (flags.length) failures += 1;
  console.log(`${flags.length ? '✖' : '✔'} ${p.viewport} кнопка=${JSON.stringify(p.heroCta)} заглушек=${p.emptySlots}${flags.length ? `\n   ${flags.join('\n   ')}` : ''}`);
}

const nj = report.noJs;
const noJsBad = nj.hidden > 0 || nj.broken.length > 0;
if (noJsBad) failures += 1;
console.log(`${noJsBad ? '✖' : '✔'} без JS: скрытых блоков ${nj.hidden}, ссылки кнопок ${nj.hrefs.join(', ')}${nj.broken.length ? ` — битые: ${nj.broken.join(', ')}` : ''}`);

const u = report.utm;
const utmBad = u.ab?.payload !== EXPECTED_PAYLOAD || u.hook !== 'math' || u.afterReturnWithoutUtm !== EXPECTED_PAYLOAD;
if (utmBad) failures += 1;
console.log(`${utmBad ? '✖' : '✔'} метка: ${u.ab?.payload}, хук: ${u.hook}, после возврата без UTM: ${u.afterReturnWithoutUtm}`);

const total = report.pages.length + 2;
console.log(failures ? `\nПроблем: ${failures} из ${total} проверок` : `\nВсе ${total} проверок чистые`);
process.exitCode = failures ? 1 : 0;
