/* Общие функции отчёта: построение DOM без innerHTML (весь текст из данных — через textContent),
   форматирование чисел и денег, подгрузка файлов превью. */
(function () {
  "use strict";

  const USD_UZS = (window.REPORT && window.REPORT.facts.usd_uzs) || 11765;
  const TIERS = [
    { key: "долгожитель (60+ дней)", cls: "long", label: "60+ дней" },
    { key: "держат (30–59 дней)", cls: "hold", label: "30–59 дней" },
    { key: "середина (15–29 дней)", cls: "mid", label: "15–29 дней" },
    { key: "рано судить (до 14 дней)", cls: "new", label: "до 14 дней" },
  ];

  function h(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value === null || value === undefined || value === false) continue;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : String(value));
    }
    for (const kid of kids.flat(Infinity)) {
      if (kid === null || kid === undefined || kid === false || kid === "") continue;
      node.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    }
    return node;
  }

  const isBlank = (v) => v === null || v === undefined || v === "" || Number.isNaN(v);
  const fmt = (n) => (isBlank(n) ? "—" : Number(n).toLocaleString("ru-RU", { maximumFractionDigits: 1 }));
  const pct = (x) => (isBlank(x) ? "—" : `${Math.round(Number(x) * 100)}%`);
  const uzs = (n) => (isBlank(n) ? "—" : `${Number(n).toLocaleString("ru-RU")} сум`);
  const usd = (n) => (isBlank(n) ? "" : `≈ $${Math.round(Number(n) / USD_UZS).toLocaleString("ru-RU")}`);
  const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : null);

  function link(url, text, cls) {
    const href = safeUrl(url);
    if (!href) return h("span", { class: cls }, text || url || "—");
    return h("a", { href, target: "_blank", rel: "noopener noreferrer", class: cls }, text || url);
  }

  function chip(text, cls) {
    return h("span", { class: `chip ${cls || "t"}` }, text);
  }

  function tierOf(key) {
    return TIERS.find((t) => t.key === key) || TIERS[2];
  }

  function tierMark(key) {
    const t = tierOf(key);
    return h("span", { class: `tier ${t.cls}` }, t.label);
  }

  /* Горизонтальная полоса долей + легенда. items: [{value, count, share}] */
  function shareBar(items, limit) {
    const top = (items || []).slice(0, limit || 5);
    const rest = (items || []).slice(limit || 5).reduce((a, x) => a + x.share, 0);
    const rows = rest > 0.001 ? [...top, { value: "остальное", share: rest, count: null }] : top;
    return h("div", { class: "legend-list-wrap" },
      h("div", { class: "bar", role: "img", "aria-label": rows.map((r) => `${r.value} ${pct(r.share)}`).join(", ") },
        rows.map((r, i) => h("span", { class: r.cls || `s${(i % 6) + 1}`, style: `width:${(r.share * 100).toFixed(2)}%` }))),
      h("div", { class: "legend-list" },
        rows.map((r, i) => h("div", {}, h("i", { class: r.cls || `s${(i % 6) + 1}` }), h("span", {}, r.value),
          h("b", {}, r.count === null ? pct(r.share) : `${pct(r.share)} · ${fmt(r.count)}`)))));
  }

  /* Сегментированный фильтр. options: [{value, label}] */
  function segmented(label, options, current, onChange) {
    const buttons = options.map((o) => h("button", {
      type: "button", "aria-pressed": String(o.value === current),
      onclick: () => {
        buttons.forEach((b) => b.setAttribute("aria-pressed", "false"));
        buttons[options.indexOf(o)].setAttribute("aria-pressed", "true");
        onChange(o.value);
      },
    }, o.label));
    return h("div", { class: "filter" }, h("span", { class: "filter-label" }, label), h("div", { class: "seg" }, buttons));
  }

  /* Подгрузка data/<kind>-<school>.js один раз. */
  const loading = {};
  function loadData(kind, school) {
    const key = `${kind}-${school}`;
    if (!loading[key]) {
      loading[key] = new Promise((resolve) => {
        const script = document.createElement("script");
        script.src = `data/${key}.js`;
        script.onload = () => resolve(true);
        script.onerror = () => resolve(false);
        document.head.append(script);
      });
    }
    return loading[key];
  }

  function table(columns, rows, cls) {
    return h("div", { class: "table-wrap" },
      h("table", { class: cls || "" },
        h("thead", {}, h("tr", {}, columns.map((c) => h("th", { class: c.cls || "" }, c.label)))),
        h("tbody", {}, rows.map((r) => h("tr", { class: r._cls || "" },
          columns.map((c) => h("td", { class: c.cls || "" }, c.render ? c.render(r) : fmt(r[c.key]))))))));
  }

  window.UI = { h, fmt, pct, uzs, usd, link, chip, tierOf, tierMark, shareBar, segmented, loadData, table, TIERS, safeUrl };
})();
