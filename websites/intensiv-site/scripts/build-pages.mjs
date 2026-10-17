// Генерирует входные HTML для Vite из шаблонов:
//   index.html — лендинг (src/template.html)
//   privacy/   — политика конфиденциальности (src/privacy.html)
// Места под фото и скриншоты ({{SLOT:имя}}) заполняются из public/img/ — см. IMAGE_SLOTS в src/config.js.
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { BOT_USERNAME, HOOK_HEADLINES, IMAGE_SLOTS, INDEXABLE, LANDING_VERSION, SITE, THEME_COLOR } from '../src/config.js';
import { buildBotUrl, buildStartPayload } from '../src/lib/attribution.js';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const template = readFileSync(resolve(root, 'src/template.html'), 'utf8');
const privacyTemplate = readFileSync(resolve(root, 'src/privacy.html'), 'utf8');

const escapeAttr = (s) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
const escapeText = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');

// Подмена заголовка под хук рекламы по utm_content — сразу после <h1>, до отрисовки.
const hookScript = `<script>(function(){var h=${JSON.stringify(HOOK_HEADLINES)},k='';try{k=(new URLSearchParams(location.search).get('utm_content')||'').toLowerCase()}catch(e){}for(var key in h){if(k.indexOf(key)>-1){var el=document.getElementById('hero-title');el.innerHTML=h[key];el.setAttribute('data-hook',key);break}}})();</script>`;

// Ссылка кнопок прямо в HTML: страница ведёт в бот, даже если JS не загрузился.
// JS потом добавит в метку UTM. Пока бот не задан — якорь на финальный блок страницы.
function staticCtaHref() {
  const payload = buildStartPayload(LANDING_VERSION, { source: '', campaign: '', content: '' });
  return buildBotUrl(BOT_USERNAME, payload) ?? '#start-now';
}

// Картинка, если файл лежит в public/, иначе заглушка с подписью, что сюда положить.
// Пропорции заглушек — в CSS (.slot--имя): встроенные style запрещены политикой CSP.
function renderSlot(name) {
  const slot = IMAGE_SLOTS[name];
  if (!slot) throw new Error(`Нет места под картинку «${name}» в IMAGE_SLOTS (src/config.js)`);
  if (existsSync(resolve(root, 'public', slot.file))) {
    const loading = slot.eager ? 'fetchpriority="high"' : 'loading="lazy" decoding="async"';
    return `<img class="slot slot--${name}" src="%BASE_URL%${slot.file}" width="${slot.width}" height="${slot.height}" alt="${escapeAttr(slot.alt)}" ${loading}>`;
  }
  return `<div class="slot slot--${name} slot--empty" role="img" aria-label="${escapeAttr(`Место для картинки: ${slot.alt}`)}"><span class="slot__title">${escapeText(slot.title)}</span><span class="slot__hint">${escapeText(slot.hint)}</span></div>`;
}

function render() {
  const html = template
    .replaceAll('{{TITLE}}', escapeAttr(SITE.title))
    .replaceAll('{{DESCRIPTION}}', escapeAttr(SITE.description))
    .replaceAll('{{OG_TITLE}}', escapeAttr(SITE.ogTitle))
    .replaceAll('{{ROBOTS}}', INDEXABLE ? 'index, follow' : 'noindex, nofollow')
    .replaceAll('{{THEME_COLOR}}', THEME_COLOR)
    .replaceAll('{{OG_IMAGE}}', `${SITE.url}og.png`)
    .replace('{{HOOK_SCRIPT}}', hookScript)
    .replace(/\{\{SLOT:([a-z0-9]+)\}\}/g, (_, name) => renderSlot(name))
    .replaceAll('href="#start"', `href="${escapeAttr(staticCtaHref())}"`)
    // CSP вставляет scripts/postbuild.mjs после сборки, когда известны хеши встроенных скриптов.
    .replace(/\s*<meta http-equiv="Content-Security-Policy" content="\{\{CSP\}\}">/, '');
  const leftover = html.match(/\{\{[A-Z_:a-z0-9]+\}\}/);
  if (leftover) throw new Error(`В шаблоне осталась незаполненная метка ${leftover[0]}`);
  return html;
}

writeFileSync(resolve(root, 'index.html'), render());
console.log('page: index.html');

// Страницы вариантов A/B (a/, b/, c/) убраны 28.09.2026 — чистим старые входы, если остались.
for (const old of ['a', 'b', 'c']) rmSync(resolve(root, old), { recursive: true, force: true });

const privacyFile = resolve(root, 'privacy/index.html');
mkdirSync(dirname(privacyFile), { recursive: true });
writeFileSync(privacyFile, privacyTemplate.replaceAll('{{ROBOTS}}', 'noindex, nofollow').replaceAll('{{THEME_COLOR}}', THEME_COLOR));
console.log('page: privacy/index.html');
