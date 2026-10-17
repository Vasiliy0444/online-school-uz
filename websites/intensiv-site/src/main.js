import './styles/main.css';
import { BOT_USERNAME, LANDING_VERSION, PIXEL_ID } from './config.js';
import { buildBotUrl, buildStartPayload, hasUtm, readUtm, resolveUtm } from './lib/attribution.js';
import { initPixel, trackLead } from './lib/pixel.js';

const UTM_STORAGE_KEY = 'ab_utm';
const TOAST_MS = 3200;

function readStoredUtm() {
  try {
    return JSON.parse(localStorage.getItem(UTM_STORAGE_KEY) ?? 'null');
  } catch {
    return null;
  }
}

function storeUtm(utm) {
  try {
    localStorage.setItem(UTM_STORAGE_KEY, JSON.stringify(utm));
  } catch {
    // Приватный режим или запрет хранилища — метка всё равно уйдёт в бот из адреса страницы.
  }
}

function showToast(text) {
  const toast = document.querySelector('.toast');
  if (!toast) return;
  toast.textContent = text;
  toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.hidden = true;
  }, TOAST_MS);
}

function setupCtas({ version, payload, botUrl }) {
  const ctas = document.querySelectorAll('[data-cta]');
  ctas.forEach((link) => {
    if (botUrl) {
      link.href = botUrl;
      link.rel = 'noopener';
    }
    link.addEventListener('click', (event) => {
      trackLead({ version, placement: link.dataset.cta, start: payload });
      if (!botUrl) {
        event.preventDefault();
        showToast('Бот ещё не подключён: ссылка появится после настройки.');
      }
    });
  });
}

// Липкая кнопка видна, когда на экране нет ни одной кнопки страницы.
function setupStickyCta() {
  const sticky = document.querySelector('.sticky-cta');
  const stickyLink = sticky?.querySelector('a');
  const pageCtas = [...document.querySelectorAll('[data-cta]')].filter((el) => !sticky?.contains(el));
  if (!sticky || !stickyLink || !pageCtas.length || !('IntersectionObserver' in window)) return;

  const visible = new Set();
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) visible.add(entry.target);
      else visible.delete(entry.target);
    });
    const show = visible.size === 0;
    sticky.classList.toggle('is-visible', show);
    sticky.setAttribute('aria-hidden', String(!show));
    stickyLink.tabIndex = show ? 0 : -1;
  });
  pageCtas.forEach((el) => observer.observe(el));
}

function init() {
  const version = LANDING_VERSION;
  const urlUtm = readUtm(window.location.search);
  if (hasUtm(urlUtm)) storeUtm(urlUtm);
  const utm = resolveUtm(urlUtm, readStoredUtm());
  const payload = buildStartPayload(version, utm);
  const botUrl = buildBotUrl(BOT_USERNAME, payload);

  // Для проверки в консоли и автотестов: какая версия лендинга и какая метка уйдут в бот.
  window.__AB = Object.freeze({ version, payload, botUrl, hook: document.getElementById('hero-title')?.dataset.hook ?? null });

  setupCtas({ version, payload, botUrl });
  setupStickyCta();
  initPixel(PIXEL_ID);
}

init();
