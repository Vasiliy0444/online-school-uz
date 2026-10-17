/* Разделы отчёта: итог, мастер-список, школы, воронки, лендинги, деньги, Google, выводы, покрытие. Данные — window.REPORT. */
(function () {
  "use strict";
  const { h, fmt, pct, uzs, usd, link, chip, tierOf, shareBar, segmented, loadData, table } = window.UI;
  const { mountGallery, openCreative, card, fillThumbs } = window.Gallery;
  const R = window.REPORT;
  const slot = (name) => document.querySelector(`[data-slot="${name}"]`);
  const STAGES = ["лид-магнит", "квиз", "вебинар или мастер-класс", "мини-курс или трипвайер", "основной продукт",
    "оферта или оплата", "страница спасибо", "главная или каталог", "прочее"];
  const quote = (f) => (f && f.found ? h("span", {}, f.value || "", f.quote ? [" ", h("q", {}, f.quote)] : null) : h("span", { class: "miss" }, "не найдено"));
  const short = (text, max = 190) => {
    if (!text || text.length <= max) return text;
    const cut = text.slice(0, max);
    return h("span", { title: text }, `${cut.slice(0, cut.lastIndexOf(" ") > 120 ? cut.lastIndexOf(" ") : max)}…`);
  };
  const MATCH_LABELS = { promise_continuity: "обещание", language_match: "язык", visual_continuity: "визуал",
    cta_alignment: "призыв", specificity_match: "конкретика", emotional_match: "эмоция" };

  function renderSummary() {
    const f = R.findings;
    if (!f) return;
    slot("headline").textContent = f.headline;
    slot("lede").textContent = f.lede;
    slot("stats").replaceChildren(...f.stats.map((s) => h("div", { class: `stat ${s.tone || ""}` }, h("b", {}, s.value), h("span", {}, s.label))));
    slot("tldr").replaceChildren(...f.tldr.map((t) => h("li", {}, h("span", {}, h("strong", {}, t.title), " ", t.text))));
  }

  function renderMaster() {
    const shortlisted = new Set(R.schools.map((s) => s.id));
    const root = slot("master");
    const columns = [
      { label: "Школа", cls: "first", render: (r) => [r.name, shortlisted.has(r.school_id) ? h("span", { class: "chip hi", title: "в разборе" }, " в разборе") : null] },
      { label: "Трек", render: (r) => r.track }, { label: "Ниша", render: (r) => r.niche },
      { label: "Активных в Meta", cls: "num", key: "meta_active" }, { label: "Уник. креативов", cls: "num", key: "unique_creatives" },
      { label: "30+ дней", cls: "num", key: "evergreen" }, { label: "За 30 дней", cls: "num", key: "recent" },
      { label: "Подписчики", cls: "num", key: "followers_max" },
      { label: "Статус", render: (r) => chip(r.status, r.status.includes("основной") ? "hi" : r.status.includes("запасной") ? "md" : "gap") },
      { label: "Не прошёл основной порог", render: (r) => r["не прошёл (основной)"] || "—" },
    ];
    const body = h("div");
    const draw = (mode) => {
      const rows = R.master.filter((r) => mode === "all" || r.status.startsWith("денежная") || shortlisted.has(r.school_id));
      body.replaceChildren(table(columns, rows, "wide"), h("p", { class: "caption" }, `Строк: ${rows.length} из ${R.master.length}.`));
    };
    root.replaceChildren(segmented("Показать", [{ value: "money", label: "денежные и в разборе" }, { value: "all", label: "все школы" }], "money", draw), body);
    draw("money");
  }

  function socialsList(s) {
    if (!s.socials.length) return h("p", { class: "small muted" }, "нет данных");
    const rows = [...s.socials].sort((a, b) => Number(b.followers) - Number(a.followers));
    return h("div", { class: "socials" }, rows.map((x) => h("div", { class: "social" },
      h("div", { class: "social-line" },
        h("span", {}, `${x.platform} `, link(x.url || null, x.handle)),
        h("b", {}, fmt(x.followers))),
      x.median_views ? h("div", { class: "note-text" }, `медиана просмотров поста ${fmt(x.median_views)}`) : null,
      x.note && !/замерить/.test(x.note) ? h("div", { class: "note-text" }, x.note) : null)));
  }

  function funnelMap(s) {
    const byStage = {};
    s.landings.filter((l) => l.analysis).forEach((l) => (byStage[l.stage] = byStage[l.stage] || []).push(l));
    const stages = STAGES.filter((st) => byStage[st]);
    if (!stages.length) return h("p", { class: "small muted" }, "Разбор лендингов ещё не готов.");
    return h("div", { class: "funnel" }, stages.map((st) => h("div", { class: `stage ${byStage[st].every((l) => l.analysis.closed) ? "closed" : ""}` },
      h("h5", {}, st), byStage[st].map((l) => link(l.url, l.url.replace(/^https?:\/\/(www\.)?/, ""))))));
  }

  function schoolPanel(s) {
    const p = s.profile;
    const counter = s.pages.reduce((a, x) => a + (Number(x.meta_counter) || 0), 0);
    const top = [...s.creatives].sort((a, b) => b.days - a.days).slice(0, 6);
    const panel = h("div", { class: "school" },
      h("div", { class: "school-head" },
        h("h3", {}, s.name),
        h("div", { class: "chips" }, chip(s.track), chip(s.niche), chip(s.status, s.status.includes("основной") ? "hi" : "md"), s.risk ? chip("зона риска", "risk") : null)),
      h("p", { class: "small" }, "Сайты: ", s.domains.length ? s.domains.map((d, i) => [i ? ", " : "", link(`https://${d}`, d)]) : "нет своего сайта в рекламе"),
      h("div", { class: "grid-3" },
        h("div", { class: "panel" }, h("h4", {}, "Реклама в Meta"),
          h("dl", { class: "kv" },
            h("dt", {}, "Счётчик Meta"), h("dd", {}, `~${fmt(counter)} объявлений`),
            h("dt", {}, "Собрано"), h("dd", {}, `${fmt(p.ads)} объявлений, ${fmt(p.unique_creatives)} уникальных креативов`),
            h("dt", {}, "За 30 дней"), h("dd", {}, `запущено ${fmt(p.launched_30d)}`),
            h("dt", {}, "Срок показа"), h("dd", {}, `медиана ${fmt(p.days_median)} дн., максимум ${fmt(p.days_max)} дн. (с ${p.oldest_start || "—"})`),
            h("dt", {}, "Длина видео"), h("dd", {}, p.video_median_s ? `медиана ${fmt(p.video_median_s)} с` : "—")),
          h("p", { class: "small" }, s.pages.map((pg, i) => [i ? " · " : "", link(pg.ad_library, `страница ${pg.page_id}`)]))),
        h("div", { class: "panel" }, h("h4", {}, "Формат объявлений"), shareBar(p.formats, 4), h("h4", {}, "Куда ведёт клик"), shareBar(p.destinations, 4)),
        h("div", { class: "panel" }, h("h4", {}, "Сколько живут креативы"),
          shareBar(window.UI.TIERS.map((tr) => p.tiers.find((t) => t.value === tr.key)).filter(Boolean)
            .map((t) => ({ ...t, value: tierOf(t.value).label, cls: `c-${tierOf(t.value).cls}` })), 4),
          h("p", { class: "small muted" }, "Доля уникальных креативов по максимальному сроку показа на 16.09.2026.")),
        h("div", { class: "panel" }, h("h4", {}, "Соцсети"), socialsList(s)),
        h("div", { class: "panel", style: "grid-column: span 2" }, h("h4", {}, "Воронка по публичным страницам"), funnelMap(s))),
      h("h4", { class: "filter-label" }, "Дольше всего идут"),
      h("div", { class: "gallery" }, top.map(card)));
    fillThumbs(panel, s.id);
    return panel;
  }

  function renderSchools() {
    const root = slot("schools");
    const holder = h("div");
    const buttons = R.schools.map((s, i) => h("button", {
      type: "button", role: "tab", "aria-selected": String(i === 0),
      onclick: () => { buttons.forEach((b) => b.setAttribute("aria-selected", "false")); buttons[i].setAttribute("aria-selected", "true"); holder.replaceChildren(schoolPanel(s)); },
    }, s.name.split(" (")[0]));
    root.replaceChildren(h("div", { class: "tabs", role: "tablist" }, buttons), holder);
    holder.replaceChildren(schoolPanel(R.schools[0]));
  }

  function renderSocials() {
    const best = (s, platform) => s.socials.filter((x) => x.platform === platform).sort((a, b) => Number(b.followers) - Number(a.followers));
    const cellFor = (platform) => (s) => {
      const list = best(s, platform);
      if (!list.length) return "—";
      return h("span", {}, list.map((x, i) => [i ? h("br") : null, link(x.url || null, x.handle), ` ${fmt(x.followers)}`,
        x.median_views ? h("span", { class: "miss" }, ` · просмотры ${fmt(x.median_views)}`) : null]));
    };
    slot("socials").replaceChildren(table([
      { label: "Школа", cls: "first", render: (s) => s.name.split(" (")[0] },
      { label: "Instagram", render: cellFor("instagram") }, { label: "Telegram", render: cellFor("telegram") },
      { label: "YouTube", render: cellFor("youtube") },
    ], R.schools, "wide"), h("p", { class: "caption" }, "Подписчики на 16.09.2026; Instagram округляет числа. Просмотры — медиана по последним постам канала Telegram."));
  }

  function renderFunnelTypes() {
    const f = R.findings;
    if (!f || !f.funnels) return;
    slot("funnel-types").replaceChildren(h("div", { class: "grid-2" }, f.funnels.map((x) => h("article", { class: "card" },
      h("h3", {}, x.title), h("p", { class: "small muted" }, x.schools), h("p", { class: "small" }, x.text)))));
  }

  function renderFunnels() {
    const columns = [{ label: "Школа", cls: "first", render: (s) => s.name.split(" (")[0] },
      ...STAGES.map((st) => ({ label: st, cls: "num", render: (s) => {
        const n = s.landings.filter((l) => l.analysis && l.stage === st).length;
        return h("span", { class: `dot ${n ? "" : "zero"}` }, n || "·");
      } })),
      { label: "Куда ведёт реклама", render: (s) => s.profile.destinations.slice(0, 2).map((d) => `${d.value} ${pct(d.share)}`).join(", ") }];
    slot("funnels").replaceChildren(table(columns, R.schools, "wide"));
  }

  function landingCard(l, school) {
    const a = l.analysis;
    const shot = ((window.SHOTS || {})[school] || {})[l.id];
    const tariffs = a.price && a.price.found && a.price.tariffs ? a.price.tariffs.map((t) => h("div", {}, `${t.name}: ${uzs(t.price_uzs)} ${usd(t.price_uzs)}`,
      t.old_price_uzs ? h("span", { class: "miss" }, ` (было ${uzs(t.old_price_uzs)})`) : null, t.period ? ` · ${t.period}` : null)) : null;
    const program = a.program && a.program.found ? [a.program.format, a.program.modules && `${a.program.modules} модулей`, a.program.lessons && `${a.program.lessons} уроков`, a.program.duration].filter(Boolean).join(", ") : null;
    return h("article", { class: "landing" },
      shot ? h("img", { src: shot, alt: `Первый экран ${l.url}` }) : h("div", { class: "ph small muted" }, "нет скриншота"),
      h("div", { class: "col" },
        h("div", { class: "chips" }, chip(a.stage, "est"), a.is_archive ? chip("архив Wayback", "md") : null, a.closed ? chip("дальше закрыто", "gap") : null, a.builder ? chip(a.builder) : null),
        link(l.url, l.url, "url"),
        h("dl", { class: "kv wide" },
          h("dt", {}, "Обещание"), h("dd", {}, quote(a.promise)),
          h("dt", {}, "Для кого"), h("dd", {}, quote(a.audience)),
          h("dt", {}, "Программа"), h("dd", {}, program || h("span", { class: "miss" }, "не найдено")),
          h("dt", {}, "Спикер"), h("dd", {}, quote(a.speaker)),
          h("dt", {}, "Доказательства"), h("dd", {}, [(a.social_proof.types || []).join(", "), a.social_proof.count_claim ? ` · «${a.social_proof.count_claim}» (самоотчёт)` : ""].join("")),
          h("dt", {}, "Цена"), h("dd", {}, tariffs || h("span", { class: "miss" }, a.price && a.price.hidden_reason ? `скрыта: ${a.price.hidden_reason}` : "не найдено")),
          h("dt", {}, "Рассрочка"), h("dd", {}, quote(a.installments)),
          h("dt", {}, "Гарантия"), h("dd", {}, quote(a.guarantee)),
          h("dt", {}, "Бонусы"), h("dd", {}, quote(a.bonuses)),
          h("dt", {}, "Дедлайн"), h("dd", {}, quote(a.deadline)),
          h("dt", {}, "Форма"), h("dd", {}, a.form.present ? (a.form.fields || []).join(", ") || "есть" : "нет"),
          h("dt", {}, "Следующий шаг"), h("dd", {}, a.next_step),
          a.notes ? [h("dt", {}, "Заметки"), h("dd", {}, a.notes)] : null),
        a.message_match && a.message_match.scores ? h("div", {},
          h("p", { class: "small" }, `Совпадение с объявлением `, link(`https://www.facebook.com/ads/library/?id=${a.message_match.library_id}`, a.message_match.library_id), `: ${a.message_match.total_of_60} из 60`),
          h("div", { class: "score-row" }, Object.entries(a.message_match.scores).map(([k, v]) => h("div", {}, h("span", {}, MATCH_LABELS[k] || k), h("b", {}, `${v}/10`))))) : null));
  }

  function renderLandings() {
    const root = slot("landings");
    const list = h("div", { class: "landings" });
    const withAnalysis = R.schools.filter((s) => s.landings.some((l) => l.analysis));
    if (!withAnalysis.length) { root.replaceChildren(h("p", { class: "muted" }, "Разбор лендингов ещё не готов.")); return; }
    const draw = (id) => {
      const s = R.schools.find((x) => x.id === id);
      loadData("shots", id).then(() => list.replaceChildren(...s.landings.filter((l) => l.analysis)
        .sort((a, b) => STAGES.indexOf(a.stage) - STAGES.indexOf(b.stage)).map((l) => landingCard(l, id))));
    };
    root.replaceChildren(segmented("Школа", withAnalysis.map((s) => ({ value: s.id, label: s.name.split(" (")[0] })), withAnalysis[0].id, draw), list);
    draw(withAnalysis[0].id);
  }

  function renderMoney() {
    const rows = R.schools.flatMap((s) => s.offers.map((o) => ({ ...o, school: s.name.split(" (")[0] })));
    if (!rows.length) { slot("money").replaceChildren(h("p", { class: "muted" }, "Цены появятся после разбора лендингов.")); return; }
    const summary = table([
      { label: "Школа", cls: "first", render: (s) => s.name.split(" (")[0] },
      { label: "Цена на сайте", render: (s) => {
        const m = R.facts[s.id].money;
        if (!m.pages) return "—";
        if (!m.price_min_uzs) return h("span", { class: "miss" }, m.hidden_price_reason ? ["скрыта: ", short(m.hidden_price_reason, 120)] : "не показана");
        return m.price_min_uzs === m.price_max_uzs ? `${uzs(m.price_min_uzs)} ${usd(m.price_min_uzs)}`
          : `${uzs(m.price_min_uzs)} — ${uzs(m.price_max_uzs)}`;
      } },
      { label: "Рассрочка", render: (s) => short(R.facts[s.id].money.installments_text) || h("span", { class: "miss" }, "не найдено") },
      { label: "Скидки и гранты", render: (s) => short(R.facts[s.id].money.discounts_text) || h("span", { class: "miss" }, "не найдено") },
      { label: "Гарантия и возврат", render: (s) => short(R.facts[s.id].money.guarantee_text) || h("span", { class: "miss" }, "не найдено") },
      { label: "Дальше", render: (s) => R.facts[s.id].money.main_next_step },
    ], R.schools, "wide");
    const details = h("details", {}, h("summary", {}, `Все тарифы со страниц (${rows.length} строк)`));
    slot("money").replaceChildren(summary, h("p", { class: "caption" }, "Диапазон — от самого дешёвого до самого дорогого тарифа на страницах школы; периоды тарифов разные (месяц, курс, разовая оплата) — см. все тарифы."), details);
    details.append(table([
      { label: "Школа", cls: "first", render: (r) => r.school }, { label: "Этап", render: (r) => r.stage },
      { label: "Тариф", render: (r) => r.tariff || (r.price_hidden_reason ? `цена скрыта: ${r.price_hidden_reason}` : "—") },
      { label: "Цена", cls: "num", render: (r) => (r.price_uzs ? uzs(r.price_uzs) : "—") },
      { label: "В долларах", cls: "num", render: (r) => usd(r.price_uzs) || "—" },
      { label: "Рассрочка", render: (r) => r.installments || "—" }, { label: "Гарантия", render: (r) => r.guarantee || "—" },
      { label: "Бонусы и дедлайн", render: (r) => [r.bonuses, r.deadline].filter(Boolean).join(" · ") || "—" },
      { label: "Страница", render: (r) => link(r.url, r.url.replace(/^https?:\/\/(www\.)?/, "").slice(0, 48)) },
    ], rows, "wide"));
  }

  function renderGoogle() {
    const g = R.google_status;
    if (!g) return;
    const ads = R.google_ads || [];
    slot("google").replaceChildren(h("p", { class: "prose" }, g.summary),
      ads.length ? table([
        { label: "Школа", cls: "first", render: (r) => r.school_id }, { label: "Рекламодатель в Google", render: (r) => r.advertiser_name },
        { label: "Формат", render: (r) => r.format }, { label: "Последний показ в Узбекистане", cls: "num", render: (r) => r.last_shown },
        { label: "Карточка", render: (r) => link(r.url, r.creative_id) },
      ], ads, "mid") : null,
      h("h3", {}, "Как проверяли"),
      table([{ label: "Когда", render: (r) => r.at }, { label: "Что делали", render: (r) => r.action }, { label: "Результат", render: (r) => r.result }], g.attempts, "mid"));
  }

  function renderFindings() {
    const f = R.findings;
    if (!f) return;
    const conf = { "высокая": "hi", "средняя": "md", "низкая": "lo" };
    slot("works").replaceChildren(...f.works.map((w) => h("div", { class: "finding" },
      h("h3", {}, w.claim, chip(`уверенность: ${w.confidence}`, conf[w.confidence] || "gap")),
      h("p", { class: "muted" }, w.evidence),
      w.examples && w.examples.length ? h("p", { class: "small" }, "Примеры: ", w.examples.map((id, i) => [i ? ", " : "",
        h("button", { type: "button", class: "linkish", onclick: () => openCreative(id) }, id)])) : null)));
    slot("gaps").replaceChildren(...f.gaps.map((g) => h("li", {}, h("span", {}, h("strong", {}, g.title), " ", g.text))));
  }

  const COMPARE_FIELDS = ["тип хука", "смысл", "оффер", "стиль", "визуал хука", "формат", "длительность", "призыв", "куда ведёт", "этап воронки", "спикер", "язык"];
  const COMPARE_GROUPS = [
    { key: "долгожитель (60+ дней)", label: "60+ дней" }, { key: "держат (30–59 дней)", label: "30–59 дней" },
    { key: "середина (15–29 дней)", label: "15–29 дней" }, { key: "рано судить (до 14 дней)", label: "до 14 дней" },
    { key: "топ-10 по показам", label: "топ-10 по показам" }, { key: "все размеченные", label: "все" },
  ];

  function renderCompare() {
    if (!R.shares || !R.shares.length) return;
    const root = slot("compare");
    const holder = h("div");
    const size = Object.fromEntries(R.shares.map((r) => [r.group, Number(r.creatives_in_group)]));
    const draw = (field) => {
      const rows = R.shares.filter((r) => r.field === field);
      const values = [...new Set(rows.filter((r) => r.group === "все размеченные").sort((a, b) => b.share - a.share).map((r) => r.value))];
      const cell = (group, value) => {
        const row = rows.find((r) => r.group === group && r.value === value);
        return row ? Number(row.share) : 0;
      };
      holder.replaceChildren(table([
        { label: field, cls: "first", render: (v) => v },
        ...COMPARE_GROUPS.map((g) => ({ label: `${g.label} (${size[g.key] || 0})`, cls: "num", render: (v) => {
          const share = cell(g.key, v);
          const lift = g.key === COMPARE_GROUPS[0].key && size[g.key] >= 8 && share - cell(COMPARE_GROUPS[3].key, v) >= 0.15;
          return h("span", { class: lift ? "chip hi" : "" }, pct(share));
        } })),
      ], values, "wide"), h("p", { class: "caption" }, "Доля размеченных креативов группы с этим значением (у креатива может быть несколько значений). Зелёным — у долгоживущих на 15+ п. п. чаще, чем у запущенных за последние 14 дней (если в группе 8+ креативов)."));
    };
    root.replaceChildren(h("h3", {}, "Долгоживущие против свежих"), segmented("Поле", COMPARE_FIELDS.map((f) => ({ value: f, label: f })), COMPARE_FIELDS[0], draw), holder);
    draw(COMPARE_FIELDS[0]);
  }

  function renderLift() {
    const rows = (R.lift || []).filter((r) => Math.abs(Number(r.lift)) >= 0.08);
    if (!rows.length) return;
    slot("lift").replaceChildren(h("h3", {}, "Чем креативы из топ-10 по показам отличаются от остальных — внутри школы"),
      h("p", { class: "prose muted small" }, "Сравнение внутри каждой школы (так стратегия школы не смешивается с качеством креатива), затем среднее по школам. Только признаки, которые встречаются минимум в трёх школах. Групп мало — это слабые сигналы, а не доказательство."),
      table([
        { label: "Поле", cls: "first", render: (r) => r.field }, { label: "Значение", render: (r) => r.value },
        { label: "Разница", cls: "num", render: (r) => h("span", { class: `chip ${Number(r.lift) > 0 ? "hi" : "lo"}` }, `${Number(r.lift) > 0 ? "+" : ""}${Math.round(Number(r.lift) * 100)} п. п.`) },
        { label: "В топ-10", cls: "num", render: (r) => `${r.top_count} из ${r.top_n}` },
        { label: "Остальные", cls: "num", render: (r) => `${r.rest_count} из ${r.rest_n}` },
        { label: "Школ", cls: "num", render: (r) => r.schools },
      ], rows, "mid"));
  }

  function renderHooks() {
    if (!R.hooks || !R.hooks.length) return;
    const root = slot("hooks");
    const names = Object.fromEntries(R.schools.map((s) => [s.id, s.name.split(" (")[0]]));
    const holder = h("div");
    const draw = (school) => {
      const rows = R.hooks.filter((x) => school === "all" || x.school_id === school).slice(0, 60);
      holder.replaceChildren(table([
        { label: "Хук дословно", cls: "first", render: (x) => h("button", { type: "button", class: "linkish", onclick: () => openCreative(x.creative_id) }, x.hook) },
        { label: "Школа", render: (x) => names[x.school_id] }, { label: "Дней", cls: "num", render: (x) => fmt(x.days_running) },
        { label: "Тип хука", render: (x) => x.hook_types }, { label: "Смысл", render: (x) => x.meaning },
        { label: "Оффер", render: (x) => x.offer }, { label: "Доход в креативе", render: (x) => (x.income_claim ? `${x.income_claim}*` : "—") },
      ], rows, "wide"), h("p", { class: "caption" }, "* заявление школы. Сначала — креативы, которые идут дольше всех."));
    };
    root.replaceChildren(h("h3", {}, "Библиотека хуков"),
      segmented("Школа", [{ value: "all", label: "все" }, ...R.schools.map((s) => ({ value: s.id, label: names[s.id] }))], "all", draw), holder);
    draw("all");
  }

  function renderAgreement() {
    const rows = R.agreement || [];
    if (!rows.length) return;
    slot("agreement").replaceChildren(h("h3", {}, "Согласие основной и слепой контрольной разметки"),
      table([
        { label: "Поле", cls: "first", render: (r) => r.field },
        { label: "Совпало", cls: "num", render: (r) => `${r.agree} из ${r.pairs}` },
        { label: "Доля", cls: "num", render: (r) => h("span", { class: `chip ${r.passes_80 === "True" ? "hi" : "md"}` }, pct(Number(r.share))) },
      ], rows, "mid"),
      h("p", { class: "caption" }, "Одиночные поля — точное совпадение, списки — пересечение не меньше половины. Порог плана — 80%; поля ниже порога читайте как ориентир, а не точную долю."));
  }

  function renderCoverage() {
    const rows = R.schools.flatMap((s) => s.pages.map((p) => ({ ...p, school: s.name.split(" (")[0] })));
    slot("coverage").replaceChildren(table([
      { label: "Школа", cls: "first", render: (r) => r.school }, { label: "Страница Meta", render: (r) => link(r.ad_library, r.page_id) },
      { label: "Счётчик Meta", cls: "num", render: (r) => fmt(r.meta_counter) }, { label: "Собрано", cls: "num", render: (r) => fmt(r.collected_ads) },
      { label: "Полнота", cls: "num", render: (r) => r.share || "—" },
      { label: "С копиями креатива", cls: "num", render: (r) => fmt(r.collected_with_copies) }, { label: "Заметки", render: (r) => r.notes || "—" },
    ], rows, "mid"));
  }

  [renderSummary, renderMaster, renderSchools, renderSocials, renderFunnelTypes, renderFunnels, renderLandings, renderMoney, renderGoogle, renderFindings, renderCompare, renderLift, renderHooks, renderAgreement, renderCoverage]
    .forEach((fn) => { try { fn(); } catch (err) { console.error(fn.name, err); } });
  mountGallery(slot("gallery"));
})();
