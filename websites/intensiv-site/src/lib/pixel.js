// Пиксель Meta (Facebook) грузится, только если в config.js задан PIXEL_ID.
const PIXEL_ID_RE = /^\d{6,20}$/;

/**
 * @param {string} pixelId
 * @returns {boolean} true, если пиксель подключён
 */
export function initPixel(pixelId) {
  if (!PIXEL_ID_RE.test(pixelId ?? '')) return false;
  if (typeof window.fbq === 'function') return true;

  const fbq = function (...args) {
    if (fbq.callMethod) fbq.callMethod(...args);
    else fbq.queue.push(args);
  };
  fbq.push = fbq;
  fbq.loaded = true;
  fbq.version = '2.0';
  fbq.queue = [];
  window.fbq = fbq;
  if (!window._fbq) window._fbq = fbq;

  const script = document.createElement('script');
  script.async = true;
  script.src = 'https://connect.facebook.net/en_US/fbevents.js';
  document.head.appendChild(script);

  fbq('init', pixelId);
  fbq('track', 'PageView');
  return true;
}

// Переход в бота считаем событием Lead: это целевое действие лендинга.
/**
 * @param {Record<string, string>} data
 * @returns {void}
 */
export function trackLead(data) {
  if (typeof window.fbq === 'function') {
    window.fbq('track', 'Lead', { content_name: 'intensiv', ...data });
  }
}
