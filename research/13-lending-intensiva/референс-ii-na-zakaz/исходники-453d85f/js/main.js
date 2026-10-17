/* «ИИ на заказ» — поведение лендинга (13.10.2026). Без библиотек. Параметры ссылки из бота и события — README.md. */
(function () {
  'use strict';
  var doc = document.documentElement;
  var qs = new URLSearchParams(location.search);
  var SHOT = !!qs.get('shot');
  if (SHOT) { doc.classList.add('shot'); document.querySelectorAll('img[loading=lazy]').forEach(function (i) { i.loading = 'eager'; }); }
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) { /* приватный режим */ } }
  };
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ================= НАСТРОЙКИ (вписывает Никита) ================= */
  // Ссылки: Telegram менеджера, оплата по тарифам, документы. Пустая строка — ссылки ещё нет:
  // тарифы ведут к блоку «Как оплатить», менеджер — к блоку «Вопросы», оферта и политика в подвале скрыты.
  // pay_pro_m5 / pay_pro_m9 — оплата «Про» по цене за медали (5–8 медалей — 1 499 990, все 9 — 1 349 990 сум);
  // пусто — кнопка «Про» ведёт на обычную ссылку pay_pro.
  var LINKS = { manager: '', pay_base: '', pay_pro: '', pay_pro_m5: '', pay_pro_m9: '', pay_mentor: '', offer: '', privacy: '' };
  // Счётчики: номер Яндекс Метрики и/или id проекта Microsoft Clarity. Пусто — не подключаются.
  var ANALYTICS = { metrika: '', clarity: '' };

  /* ---------- аналитика: события в window.dataLayer (и в Метрику, если она подключена) ---------- */
  window.dataLayer = window.dataLayer || [];
  function track(event, params) {
    var e = { event: event }; for (var k in params || {}) e[k] = params[k];
    window.dataLayer.push(e);
    try { if (ANALYTICS.metrika && window.ym) window.ym(+ANALYTICS.metrika, 'reachGoal', event, params || {}); } catch (x) { /* счётчик не загрузился */ }
  }
  if (ANALYTICS.metrika && !SHOT) {
    (function (m, e, t, r, i, k, a) { m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); }; m[i].l = 1 * new Date();
      k = e.createElement(t); a = e.getElementsByTagName(t)[0]; k.async = 1; k.src = r; a.parentNode.insertBefore(k, a); })
    (window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js', 'ym');
    window.ym(+ANALYTICS.metrika, 'init', { clickmap: true, trackLinks: true, accurateTrackBounce: true, webvisor: true });
  }
  if (ANALYTICS.clarity && !SHOT) {
    (function (c, l, a, r, i, t, y) { c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      t = l.createElement(r); t.async = 1; t.src = 'https://www.clarity.ms/tag/' + i; y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y); })
    (window, document, 'clarity', 'script', ANALYTICS.clarity);
  }

  /* ---------- метка из бота и UTM: запоминаем и пробрасываем в ссылки оплаты и менеджера ---------- */
  var PASS = ['ref', 'uid', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'];
  var attrib = {};
  try { attrib = JSON.parse(store.get('attrib') || '{}') || {}; } catch (e) { attrib = {}; }
  PASS.forEach(function (k) { var v = qs.get(k); if (v) attrib[k] = v.slice(0, 120); });
  store.set('attrib', JSON.stringify(attrib));
  function withAttrib(u) {
    try {
      var url = new URL(u);
      if (/(^|\.)t\.me$/.test(url.hostname)) {           // Telegram: метка — в start (только [A-Za-z0-9_-], до 64 знаков)
        var st = (attrib.ref || attrib.uid || '').replace(/[^A-Za-z0-9_-]/g, '').slice(0, 64);
        if (st && !url.searchParams.get('start')) url.searchParams.set('start', st);
      } else {
        PASS.forEach(function (k) { if (attrib[k] && !url.searchParams.get(k)) url.searchParams.set(k, attrib[k]); });
      }
      return url.toString();
    } catch (e) { return u; }
  }
  /* ---------- медали из бота (?m=0…9): своя цена «Про» по ступени; медали сгорают вместе со спецценой ---------- */
  var medals = null, mq = qs.get('m');
  if (mq !== null && /^\d$/.test(mq)) { medals = +mq; store.set('offer_medals', mq); }
  else { var ms = store.get('offer_medals'); if (ms !== null && /^\d$/.test(ms)) medals = +ms; }
  var tier = medals === null ? null : (medals >= 9 ? 9 : medals >= 5 ? 5 : 0);
  if (tier !== null) {
    doc.classList.add('has-medals', 'mt-' + tier, 'from-bot');
    $$('[data-medals]').forEach(function (el) { el.textContent = String(medals); });
    if (tier && LINKS['pay_pro_m' + tier]) LINKS.pay_pro = LINKS['pay_pro_m' + tier];
  }
  $$('[data-link]').forEach(function (a) {
    var key = a.getAttribute('data-link'), u = LINKS[key];
    if (u) { a.href = /^https?:/.test(u) ? withAttrib(u) : u; if (/^https?:/.test(u)) { a.target = '_blank'; a.rel = 'noopener'; } }
    else if (key === 'offer' || key === 'privacy') a.hidden = true;
  });
  document.addEventListener('click', function (e) {
    var a = e.target.closest('[data-track]'); if (!a) return;
    var kind = a.getAttribute('data-track'), place = a.getAttribute('data-place') || '';
    if (kind === 'tariff') {
      var t = a.getAttribute('data-tariff'), mt = t === 'pro' && tier !== null && !doc.classList.contains('deadline-over') ? tier : '';
      track('tariff_click', { tariff: t, medals_tier: mt }); if (LINKS['pay_' + t]) track('pay_click', { tariff: t, medals_tier: mt });
    }
    else if (kind === 'manager') track('manager_click', { place: place, linked: !!LINKS.manager });
    else track('cta_click', { place: place });
  });

  /* ---------- язык RU / UZ: переключатель виден, только когда есть перевод (флаг в strings.json → window.I18N_UZ) ---------- */
  var UZ = !!window.I18N_UZ;
  var RU_CACHE = {};
  function applyLang(lang) {
    var D = window.I18N || {};
    if (!D[lang] || (lang === 'uz' && !UZ)) lang = 'ru';
    var t = D[lang];
    $$('[data-i18n]').forEach(function (el) {
      var k = el.getAttribute('data-i18n');
      if (!(k in RU_CACHE)) RU_CACHE[k] = el.innerHTML;
      var v = lang === 'ru' ? RU_CACHE[k] : (t[k] == null ? null : String(t[k]).replace(/(\d)–(\d)/g, '$1⁠–⁠$2'));
      // в шрифте заголовков нет ʻ (U+02BB) — в узбекских заголовках пишем ‘ (o‘, g‘)
      if (v != null && lang === 'uz' && /Sofia/.test(getComputedStyle(el).fontFamily)) v = v.replace(/ʻ/g, '‘');
      if (v != null && el.innerHTML !== v) el.innerHTML = v;
    });
    ['alt', 'aria-label'].forEach(function (a) {
      $$('[data-i18n-' + a + ']').forEach(function (el) {
        var k = el.getAttribute('data-i18n-' + a);
        if (t[k] != null) el.setAttribute(a, String(t[k]).replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' '));
      });
    });
    doc.lang = lang;
    $$('[data-lang]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-lang') === lang)); });
    store.set('lang', lang);
    calc(); counter(); tick();
    requestAnimationFrame(layoutScreens);
  }
  if (!UZ) $$('.lang').forEach(function (g) { g.hidden = true; });
  $$('[data-lang]').forEach(function (b) { b.addEventListener('click', function () { applyLang(b.getAttribute('data-lang')); track('lang_switch', { lang: b.getAttribute('data-lang') }); }); });

  /* ---------- экран телефона: HTML натягивается на четырёхугольник экрана (гомография → matrix3d) ---------- */
  function solve(A, b) { // Гаусс 8×8
    var n = b.length, M = A.map(function (r, i) { return r.concat([b[i]]); });
    for (var c = 0; c < n; c++) {
      var p = c; for (var r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
      var tmp = M[c]; M[c] = M[p]; M[p] = tmp;
      for (r = 0; r < n; r++) if (r !== c) { var f = M[r][c] / M[c][c]; for (var k = c; k <= n; k++) M[r][k] -= f * M[c][k]; }
    }
    return M.map(function (r, i) { return r[n] / r[i]; });
  }
  function homography(src, dst) {
    var A = [], b = [];
    for (var i = 0; i < 4; i++) {
      var x = src[i][0], y = src[i][1], u = dst[i][0], v = dst[i][1];
      A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.push(u);
      A.push([0, 0, 0, x, y, 1, -v * x, -v * y]); b.push(v);
    }
    var h = solve(A, b);
    return [h[0], h[3], 0, h[6], h[1], h[4], 0, h[7], 0, 0, 1, 0, h[2], h[5], 0, 1];
  }
  function layoutScreens() {
    $$('.screen[data-quad]').forEach(function (s) {
      var box = s.parentElement.getBoundingClientRect();
      if (!box.width || !s.offsetWidth) return;
      var q = s.getAttribute('data-quad').split(',').map(Number);
      var w = s.offsetWidth, h = s.offsetHeight;
      var dst = [[q[0], q[1]], [q[2], q[3]], [q[4], q[5]], [q[6], q[7]]].map(function (p) { return [p[0] / 100 * box.width, p[1] / 100 * box.height]; });
      var m = homography([[0, 0], [w, 0], [w, h], [0, h]], dst);
      s.style.transform = 'matrix3d(' + m.map(function (v) { return +v.toFixed(8); }).join(',') + ')';
      s.classList.add('ready');
    });
  }
  window.addEventListener('resize', layoutScreens);
  if (window.ResizeObserver) { var ro = new ResizeObserver(layoutScreens); $$('.screen[data-quad]').forEach(function (s) { ro.observe(s.parentElement); }); }

  /* ---------- рваная диагональ блока 4 ---------- */
  function tear() {
    var svg = $('.era-tear'); if (!svg) return;
    var mob = matchMedia('(max-width: 767px)').matches;
    var x0 = mob ? 62 : 82, x1 = mob ? 40 : 52, seed = 7, d = 'M' + x0 + ',0';
    function rnd() { seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
    for (var i = 1; i <= 70; i++) { var t = i / 70; d += ' L' + (x0 + (x1 - x0) * t + (rnd() - .5) * 1.6).toFixed(2) + ',' + (t * 100).toFixed(2); }
    svg.querySelector('path').setAttribute('d', d);
  }
  tear(); window.addEventListener('resize', tear);

  /* ---------- ленты со стрелкой и точки карусели ---------- */
  $$('.hs-wrap').forEach(function (w) {
    var list = $('.hscroll', w), btn = $('.hs-next', w); if (!list || !btn) return;
    function upd() { var end = list.scrollLeft + list.clientWidth >= list.scrollWidth - 8; w.classList.toggle('at-end', end); }
    btn.addEventListener('click', function () {
      var end = list.scrollLeft + list.clientWidth >= list.scrollWidth - 8;
      list.scrollBy({ left: end ? -list.scrollWidth : list.clientWidth * .8, behavior: 'smooth' });
    });
    list.addEventListener('scroll', upd, { passive: true }); upd();
  });
  $$('[data-carousel]').forEach(function (list) {
    var dots = list.closest('.who-copy') && $('.dots', list.closest('.who-copy')); if (!dots) return;
    var items = $$(':scope > li', list);
    dots.innerHTML = items.map(function () { return '<i></i>'; }).join('');
    function upd() {
      var x = list.scrollLeft, best = 0, bd = 1e9;
      items.forEach(function (it, i) { var d = Math.abs(it.offsetLeft - list.offsetLeft - x - parseFloat(getComputedStyle(list).paddingLeft || 0)); if (d < bd) { bd = d; best = i; } });
      $$('i', dots).forEach(function (d, i) { d.classList.toggle('on', i === best); });
    }
    list.addEventListener('scroll', upd, { passive: true }); upd();
  });

  /* ---------- блок 2: живой счётчик отмеченных пунктов ---------- */
  function counter() {
    var box = $('.who-copy'); if (!box) return;
    var n = $$('.checks input:checked', box).length, out = $('[data-count]', box);
    if (out) out.textContent = n;
    box.classList.toggle('enough', n >= 2);
  }
  $$('.checks input').forEach(function (i) { i.addEventListener('change', function () { counter(); track('quiz_check', { checked: $$('.checks input:checked').length }); }); });
  counter();

  /* ---------- меню ---------- */
  var menu = $('#menu'), burger = $('.burger');
  function menuOpen(o) { if (!menu) return; menu.classList.toggle('open', o); burger && burger.setAttribute('aria-expanded', String(o)); document.body.style.overflow = o ? 'hidden' : ''; }
  burger && burger.addEventListener('click', function () { menuOpen(true); });
  menu && menu.addEventListener('click', function (e) { if (e.target.closest('a') || e.target.closest('.menu-close')) menuOpen(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { menuOpen(false); closeVideo(); } });

  /* ---------- нижняя панель «Выбрать тариф» + менеджер: после первого экрана; прячется, пока на экране тарифы, финал
     или другая кнопка «Выбрать…» — двух одинаковых кнопок на экране не бывает ---------- */
  var dock = $('.dock'), heroCta = $('#cta-hero');
  if (dock && heroCta) {
    // любая другая главная кнопка на экране (по смыслу, а не по тексту: подписи разные) + блоки тарифов и финала
    var watch = $$('a.btn[data-track="cta"], a.btn[data-track="tariff"], a.btn-o[data-track="tariff"]').filter(function (a) { return !a.closest('.dock') && !a.closest('.menu'); })
      .concat([$('#tariffs'), $('#final')].filter(Boolean));
    var onScreen = new Map();
    var updDock = function () {
      var passed = heroCta.getBoundingClientRect().bottom < 0;
      var busy = false; onScreen.forEach(function (v) { if (v) busy = true; });
      var on = passed && !busy;
      dock.classList.toggle('show', on); doc.classList.toggle('dock-on', on);
    };
    if ('IntersectionObserver' in window) {
      var dio = new IntersectionObserver(function (es) { es.forEach(function (e) { onScreen.set(e.target, e.isIntersecting); }); updDock(); });
      watch.forEach(function (el) { dio.observe(el); });
    }
    window.addEventListener('scroll', updDock, { passive: true }); updDock();
  }

  /* ---------- таймер спеццены: только по дедлайну из ссылки бота (?deadline=<unix>), без перезапусков ---------- */
  // Нет дедлайна → плашки «Новая цена» и таймера нет, только цены. После нуля — «спеццена закончилась», медали сгорают.
  var deadline = 0, dq = qs.get('deadline') || qs.get('t');
  if (dq && /^\d{9,13}$/.test(dq)) { deadline = +dq < 1e12 ? +dq * 1000 : +dq; store.set('offer_deadline', String(deadline)); }
  else deadline = +store.get('offer_deadline') || 0;
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  var lastState = '';
  function tick() {
    var state = !deadline ? 'none' : (Date.now() >= deadline ? 'over' : 'live');
    doc.classList.toggle('has-deadline', state === 'live');
    doc.classList.toggle('deadline-over', state === 'over');
    if (state !== lastState) { lastState = state; track('offer_timer', { state: state }); }
    if (state !== 'live') return;
    var s = Math.floor((deadline - Date.now()) / 1000), h = Math.floor(s / 3600);
    var txt = (h < 100 ? pad(h) : h) + ':' + pad(Math.floor(s % 3600 / 60)) + ':' + pad(s % 60);
    $$('[data-timer]').forEach(function (el) { el.textContent = txt; });
  }
  tick(); setInterval(tick, 1000);

  /* ---------- калькулятор дохода (блок 6): цены — нижние границы канона, курс ≈ 11 800 ---------- */
  var RATE = 11800, calcTimer;
  function fmt(n) { return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' '); }
  function calc() {
    var box = $('[data-calc]'); if (!box) return;
    var sum = 0, vals = {};
    $$('input[type=range]', box).forEach(function (r) {
      var v = +r.value, p = +r.getAttribute('data-price');
      sum += v * p; vals[r.name] = v;
      var out = box.querySelector('[data-out="' + r.name + '"]'); if (out) out.textContent = v;
      var pct = (v - r.min) / (r.max - r.min) * 100; r.style.setProperty('--p', pct + '%');
    });
    $$('[data-sum]', box).forEach(function (el) { el.textContent = fmt(sum); });
    $$('[data-usd]', box).forEach(function (el) { var u = Math.round(sum / RATE); el.textContent = '$' + (u < 10000 ? String(u) : fmt(u)); });
    return { sum: sum, vals: vals };
  }
  $$('[data-calc] input[type=range]').forEach(function (r) {
    r.addEventListener('input', function () { var c = calc(); clearTimeout(calcTimer); calcTimer = setTimeout(function () { track('calc_change', { sites: c.vals.sites, bots: c.vals.bots, design: c.vals.design, sum: c.sum }); }, 600); });
  });
  calc();

  /* ---------- блок 5: выбор одного скилла ---------- */
  $$('.skill').forEach(function (s) {
    s.addEventListener('click', function () { $$('.skill').forEach(function (o) { o.classList.toggle('on', o === s); o.setAttribute('aria-pressed', String(o === s)); }); track('skill_pick', { skill: ($('.skill-n', s) || s).textContent.trim() }); });
  });

  /* ---------- вкладки оплаты ---------- */
  $$('[role=tablist]').forEach(function (tl) {
    var tabs = $$('[role=tab]', tl);
    tabs.forEach(function (t) {
      t.addEventListener('click', function () {
        tabs.forEach(function (o) { var on = o === t; o.setAttribute('aria-selected', String(on)); var p = document.getElementById(o.getAttribute('aria-controls')); if (p) p.hidden = !on; });
        track('pay_tab', { tab: t.id });
      });
    });
  });

  var acted = false; ['pointerdown', 'keydown', 'touchstart'].forEach(function (t) { document.addEventListener(t, function () { acted = true; }, { passive: true, once: true }); });
  /* ---------- аккордеоны: открыт один ---------- */
  $$('[data-acc]').forEach(function (acc) {
    $$('details', acc).forEach(function (d) {
      d.addEventListener('toggle', function () {
        if (!d.open) return;
        $$('details', acc).forEach(function (o) { if (o !== d) o.open = false; });
        var q = $('summary [data-i18n]', d); if (acted) track(acc.classList.contains('qas') ? 'faq_open' : 'program_open', { item: q ? q.getAttribute('data-i18n') : '' });
      });
    });
  });

  /* ---------- видео (блок 14 собирается, только если есть файл записи) ---------- */
  var vm = $('#video-modal');
  function closeVideo() { if (!vm || vm.hidden) return; var v = $('video', vm); v && v.pause(); vm.hidden = true; document.body.style.overflow = ''; }
  $$('[data-video]').forEach(function (b) {
    b.addEventListener('click', function () {
      if (!vm) return; vm.hidden = false; document.body.style.overflow = 'hidden';
      var v = $('video', vm);
      if (!v.getAttribute('src')) v.setAttribute('src', b.getAttribute('data-video'));
      var p = v.play(); p && p.catch(function () {});
      track('video_play', {});
    });
  });
  vm && vm.addEventListener('click', function (e) { if (e.target === vm || e.target.closest('.vm-close')) closeVideo(); });

  /* ---------- просмотр блоков: событие block_view один раз на блок ---------- */
  if ('IntersectionObserver' in window && !SHOT) {
    var seen = {};
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        var b = e.target.getAttribute('data-b');
        if (e.isIntersecting && !seen[b]) { seen[b] = 1; track('block_view', { block: +b, id: e.target.id || '' }); io.unobserve(e.target); }
      });
    }, { threshold: .35 });
    $$('[data-b]').forEach(function (s) { io.observe(s); });
  }

  /* ---------- микроанимации со смыслом: один раз при появлении блока; при prefers-reduced-motion и в режиме снимка всё статично ---------- */
  var ANIM = doc.classList.contains('anim') && 'IntersectionObserver' in window;
  function once(el, fn, thr) {
    if (!el) return;
    if (!ANIM) return;
    var io2 = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { io2.disconnect(); fn(); } }); }, { threshold: thr || .35 });
    io2.observe(el);
  }
  if (ANIM) {
    // блок 1: переписка собирается по шагам — вопрос клиента, ответ с ценой, «Договорились»
    $$('.screen .chat, .chat-float').forEach(function (c) {
      once(c, function () { $$('.msg', c).forEach(function (m, i) { setTimeout(function () { m.classList.add('on'); }, 250 + i * 900); }); }, .2);
    });
    // блок 3: «49%» считает от нуля (слова из словаря не трогаем: меняем только число, в конце возвращаем исходный текст)
    var num = $('.bignum');
    if (num) {
      var orig = num.innerHTML, m = num.textContent.match(/(\d+)/), target = m ? +m[1] : 0;
      if (target) {
        num.textContent = num.textContent.replace(/\d+/, '0');
        once(num, function () {
          var t0 = performance.now(), dur = 1200;
          (function step(t) { var k = Math.min(1, (t - t0) / dur), v = Math.round(target * (1 - Math.pow(1 - k, 3)));
            num.textContent = orig.replace(/<[^>]+>/g, '').replace(/\d+/, v); if (k < 1) requestAnimationFrame(step); else num.innerHTML = orig; })(t0);
        }, .5);
      }
    }
    // блок 4: «Сайт готов 100%» обгоняет «3%»
    var era = $('.era-scene'); once(era, function () { era.classList.add('on'); }, .4);
    // блок 10 «Уровни»: метки маршрута загораются по очереди, LVL 100 последним
    var route = $('.route'); once(route, function () { route.classList.add('on'); }, .3);
  }

  /* ---------- старт ---------- */
  var saved = qs.get('lang') || store.get('lang');
  if (saved && saved !== 'ru' && UZ) applyLang(saved); else { $$('[data-lang]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-lang') === 'ru')); }); }
  track('page_view', { ref: attrib.ref || '', uid: attrib.uid || '', utm_source: attrib.utm_source || '', has_deadline: !!deadline, medals: medals === null ? '' : medals });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(layoutScreens);
  window.addEventListener('load', layoutScreens);
  layoutScreens();
})();
