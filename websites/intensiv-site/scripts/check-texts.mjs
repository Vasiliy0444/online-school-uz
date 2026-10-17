// Сверка текстов: каждая согласованная строка из LANDING_PROTOTYPE_RU.md (блоки 1, 2, 4)
// и черновика блока 3 (ЧЕРНОВИКИ.md) должна дословно быть на собранной странице docs/index.html.
// Запуск после `npm run build`: npm run check:texts
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { HOOK_HEADLINES } from '../src/config.js';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const researchDir = resolve(root, '../../research/13-lending-intensiva');
const PROTOTYPE = resolve(researchDir, 'LANDING_PROTOTYPE_RU.md');
const DRAFTS = resolve(researchDir, 'ЧЕРНОВИКИ.md');

const normalize = (s) =>
  s
    .replace(/ /g, ' ')
    .replace(/\*\*/g, '')
    .replace(/`/g, '')
    .replace(/^[\s>]*[-✓🎁🔒]*\s*/u, '')
    .replace(/[🎁🔒✓]/gu, '')
    .replace(/\s+/g, ' ')
    .trim();

const VALUE_LABELS = new Set([
  'Логотип',
  'Заголовок (H1)',
  'Строка-акцент под заголовком',
  'Подзаголовок',
  'Кнопка',
  'Под кнопкой',
  'Заголовок (H2)',
  'Бонус за регистрацию',
  'Подпись',
]);
const SKIP_REST = ['**Опция', '**Заметки', '**Откуда'];

function approvedStrings(md) {
  const out = [];
  let block = null;
  let skipping = false;
  for (const raw of md.split('\n')) {
    const line = raw.trim();
    const section = line.match(/^## Блок (\d)/);
    if (section) {
      block = Number(section[1]);
      skipping = false;
      continue;
    }
    if (![1, 2, 4].includes(block) || !line || line === '---') continue;
    if (SKIP_REST.some((p) => line.startsWith(p))) {
      skipping = true;
      continue;
    }
    if (skipping || line.startsWith('**Фото:')) continue;

    const labelled = line.match(/^\*\*([^*]+?):\*\*\s*(.*)$/);
    if (labelled) {
      const [, label, value] = labelled;
      if (label === 'Плашки') value.split('·').forEach((p) => out.push(normalize(p)));
      else if (label === 'Подвал') value.split(' · ').forEach((p) => out.push(normalize(p)));
      else if (label === 'Результат' || label === 'Задание') out.push(normalize(`${label}: ${value}`));
      else if (VALUE_LABELS.has(label)) out.push(normalize(value));
      else if (!value) out.push(normalize(`${label}:`));
      continue;
    }
    const lesson = line.match(/^\*\*(Урок \d)\. (.+)\*\*$/);
    if (lesson) {
      out.push(lesson[1], normalize(lesson[2]));
      continue;
    }
    out.push(normalize(line));
  }
  return [...new Set(out.filter(Boolean))];
}

function draftStrings(md) {
  const out = [];
  const omitted = [];
  const body = md.split('## Блок 3')[1]?.split('\nЧто нужно')[0] ?? '';
  for (const raw of body.split('\n')) {
    if (!raw.startsWith('>')) continue;
    let line = raw.replace(/^>\s?/, '').replace(/^###\s*/, '').trim();
    if (!line) continue;
    if (/подтвердить/i.test(line) || /^\[живое фото/.test(line)) {
      omitted.push(normalize(line));
      continue;
    }
    const host = line.match(/^\*\*(.+?)\*\* — (.+)$/);
    if (host) {
      out.push(normalize(host[1]), normalize(host[2]));
      continue;
    }
    out.push(normalize(line));
  }
  return { strings: [...new Set(out.filter(Boolean))], omitted };
}

function pageText(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/g, ' ')
    .replace(/<style[\s\S]*?<\/style>/g, ' ')
    .replace(/<\/(p|li|h[1-6]|div|summary|details|section|article|header|footer|main|aside|ul)>/g, ' ')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, '&')
    .replace(/ /g, ' ')
    .replace(/\s+/g, ' ');
}

const prototype = readFileSync(PROTOTYPE, 'utf8');
const approved = approvedStrings(prototype);
const draft = draftStrings(readFileSync(DRAFTS, 'utf8'));

let missingTotal = 0;
const text = pageText(readFileSync(resolve(root, 'docs/index.html'), 'utf8'));
const missing = approved.filter((s) => !text.includes(s));
const missingDraft = draft.strings.filter((s) => !text.includes(s));
missingTotal += missing.length + missingDraft.length;
console.log(`docs/index.html: согласованные ${approved.length - missing.length}/${approved.length}, черновик блока 3 ${draft.strings.length - missingDraft.length}/${draft.strings.length}`);
missing.forEach((s) => console.log(`   ✖ нет на странице: «${s}»`));
missingDraft.forEach((s) => console.log(`   ✖ нет из черновика: «${s}»`));

// Снятое с сайта 28.09.2026 (ЧЕРНОВИКИ.md, «Снято») не должно вернуться случайно
const REMOVED = ['Почему нам можно верить', 'Мы не обещаем денег без работы'];
const returned = REMOVED.filter((s) => text.includes(s));
missingTotal += returned.length;
returned.forEach((s) => console.log(`   ✖ снятый текст снова на странице: «${s}»`));

// Заголовки под хуки рекламы: config.js против таблицы в прототипе
const hookRows = [...prototype.matchAll(/^\| (Сравнение|Математика|Почему сейчас|С нуля) \| (.+?) \|$/gm)].map((m) => normalize(m[2]));
const hookTexts = Object.values(HOOK_HEADLINES).map((h) => normalize(h.replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ')));
const hookMissing = hookRows.filter((row) => !hookTexts.includes(row));
missingTotal += hookMissing.length;
console.log(`заголовки под хуки: ${hookRows.length - hookMissing.length}/${hookRows.length}`);
hookMissing.forEach((s) => console.log(`   ✖ нет в config.js: «${s}»`));

console.log(`намеренно не выведено из черновика (ждёт подтверждения): ${draft.omitted.length}`);
draft.omitted.forEach((s) => console.log(`   · ${s}`));
console.log(missingTotal ? `\nРасхождений: ${missingTotal}` : '\nВсе тексты на месте');
process.exitCode = missingTotal ? 1 : 0;
