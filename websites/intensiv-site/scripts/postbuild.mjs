// После `vite build`: считает sha256 встроенных скриптов и вставляет CSP мета-тегом в каждую страницу docs/.
// GitHub Pages не даёт задать заголовки ответа, поэтому политика — в <meta http-equiv>.
import { createHash } from 'node:crypto';
import { readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { BASE_PATH } from '../src/config.js';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const docs = resolve(root, 'docs');

function htmlFiles(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return name === 'assets' ? [] : htmlFiles(path);
    return name.endsWith('.html') ? [path] : [];
  });
}

function inlineScriptHashes(html) {
  const hashes = [];
  const re = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g;
  let match;
  while ((match = re.exec(html))) {
    const body = match[1];
    if (!body.trim()) continue;
    hashes.push(`'sha256-${createHash('sha256').update(body, 'utf8').digest('base64')}'`);
  }
  return hashes;
}

function csp(hashes) {
  return [
    "default-src 'self'",
    ["script-src 'self'", ...hashes, 'https://connect.facebook.net'].join(' '),
    "style-src 'self'",
    "img-src 'self' data: https://www.facebook.com",
    "font-src 'self'",
    "connect-src 'self' https://www.facebook.com https://connect.facebook.net",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'none'",
    'upgrade-insecure-requests',
  ].join('; ');
}

// Предзагрузка шрифтов первого экрана: шрифт заголовков и кириллица Inter 400.
const assets = readdirSync(resolve(docs, 'assets'));
const findFont = (prefix) => assets.find((name) => name.startsWith(prefix) && name.endsWith('.woff2'));
const PRELOAD_FONTS = ['roboto-flex-display-', 'inter-cyrillic-400-normal-'];

function preloadTags() {
  return PRELOAD_FONTS.map((prefix) => {
    const name = findFont(prefix);
    if (!name) throw new Error(`Не нашёл шрифт ${prefix}*.woff2 в docs/assets — проверьте импорт шрифтов в src/styles/main.css`);
    return `<link rel="preload" as="font" type="font/woff2" href="${BASE_PATH}assets/${name}" crossorigin>`;
  });
}

for (const file of htmlFiles(docs)) {
  const html = readFileSync(file, 'utf8');
  if (html.includes('http-equiv="Content-Security-Policy"')) continue;
  const meta = `<meta http-equiv="Content-Security-Policy" content="${csp(inlineScriptHashes(html))}">`;
  const head = [meta, ...(file.includes('/privacy/') ? [] : preloadTags())].join('\n    ');
  const withCsp = html.replace(/<meta charset="utf-8">/i, (m) => `${m}\n    ${head}`);
  if (withCsp === html) throw new Error(`Не нашёл <meta charset> в ${file}`);
  writeFileSync(file, withCsp);
  console.log(`csp + preload: ${file.replace(`${root}/`, '')}`);
}

writeFileSync(resolve(docs, '.nojekyll'), '');
console.log('docs/.nojekyll');
