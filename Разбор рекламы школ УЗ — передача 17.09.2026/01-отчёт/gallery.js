/* Галерея креативов Meta: фильтры, карточки, окно с текстом объявления, расшифровкой и тегами. */
(function () {
  "use strict";
  const { h, fmt, link, chip, tierMark, segmented, loadData, TIERS } = window.UI;
  const R = window.REPORT;
  const PAGE = 48;
  const FORMAT_LABEL = { VIDEO: "видео", IMAGE: "картинка", DCO: "динамическое", CAROUSEL: "карусель" };
  const schoolName = Object.fromEntries(R.schools.map((s) => [s.id, s.name]));
  const all = R.schools.flatMap((s) => s.creatives);
  const byId = Object.fromEntries(all.map((c) => [c.id, c]));

  const duration = (s) => (s ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}` : "");
  const thumbOf = (c) => ((window.THUMBS || {})[c.school] || {})[c.id];

  function hookText(c) {
    if (c.tags && c.tags.hook) return c.tags.hook;
    return (c.text || "").slice(0, 140) || "без текста";
  }

  function card(c) {
    const img = h("img", { alt: "", loading: "lazy", "data-thumb": c.id, hidden: true });
    const src = thumbOf(c);
    if (src) { img.src = src; img.hidden = false; }
    return h("button", { type: "button", class: "ad", onclick: () => openCreative(c.id), "aria-label": `${schoolName[c.school]}: ${hookText(c)}` },
      h("div", { class: "frame" },
        img,
        src ? null : h("div", { class: "ph" }, c.has_thumb ? "превью загружается" : "нет превью"),
        h("span", { class: "badge tl" }, [FORMAT_LABEL[c.format] || c.format, duration(c.duration_s)].filter(Boolean).join(" ")),
        c.ads > 1 ? h("span", { class: "badge tr", title: "объявлений с этим креативом" }, `×${c.ads}`) : null,
        c.rank ? h("span", { class: "badge bl", title: "место в первых 30 по показам" }, `№${c.rank}`) : null),
      h("div", { class: "meta" }, tierMark(c.tier), h("span", {}, `${fmt(c.days)} дн.`), c.tags ? h("span", {}, "теги") : null),
      h("div", { class: "hook" }, hookText(c)),
      h("div", { class: "school" }, schoolName[c.school]));
  }

  function fillThumbs(root, school) {
    loadData("thumbs", school).then(() => {
      root.querySelectorAll("img[data-thumb]").forEach((img) => {
        const c = byId[img.dataset.thumb];
        const src = c && thumbOf(c);
        if (src && img.hidden) {
          img.src = src;
          img.hidden = false;
          const ph = img.parentElement.querySelector(".ph");
          if (ph) ph.remove();
        }
      });
    });
  }

  function mountGallery(root) {
    const state = { school: "all", tier: "all", format: "all", tagged: "all", sort: "days", shown: PAGE };
    const grid = h("div", { class: "gallery" });
    const count = h("p", { class: "count-line" });
    const more = h("button", { type: "button", class: "more", onclick: () => { state.shown += PAGE; draw(); } }, "Показать ещё");
    const sorters = {
      days: (a, b) => b.days - a.days,
      rank: (a, b) => (a.rank || 99) - (b.rank || 99) || b.days - a.days,
      fresh: (a, b) => (b.first_started || "").localeCompare(a.first_started || ""),
      copies: (a, b) => b.ads - a.ads || b.days - a.days,
    };
    const reset = (key) => (value) => { state[key] = value; state.shown = PAGE; draw(); };

    function draw() {
      const items = all.filter((c) => (state.school === "all" || c.school === state.school)
        && (state.tier === "all" || c.tier === state.tier)
        && (state.format === "all" || c.format === state.format)
        && (state.tagged === "all" || Boolean(c.tags)))
        .sort(sorters[state.sort]);
      grid.replaceChildren(...items.slice(0, state.shown).map(card));
      count.replaceChildren("Показано ", h("b", {}, fmt(Math.min(state.shown, items.length))), " из ", h("b", {}, fmt(items.length)), " креативов");
      more.hidden = items.length <= state.shown;
      new Set(items.slice(0, state.shown).map((c) => c.school)).forEach((s) => fillThumbs(grid, s));
    }

    const formats = [...new Set(all.map((c) => c.format))].filter(Boolean);
    root.replaceChildren(
      h("div", { class: "filters" },
        segmented("Школа", [{ value: "all", label: "все" }, ...R.schools.map((s) => ({ value: s.id, label: s.name.split(" (")[0] }))], "all", reset("school")),
        segmented("Срок показа", [{ value: "all", label: "любой" }, ...TIERS.map((t) => ({ value: t.key, label: t.label }))], "all", reset("tier")),
        segmented("Формат", [{ value: "all", label: "все" }, ...formats.map((f) => ({ value: f, label: FORMAT_LABEL[f] || f }))], "all", reset("format")),
        segmented("Разметка", [{ value: "all", label: "все" }, { value: "tagged", label: "с тегами" }], "all", reset("tagged")),
        segmented("Порядок", [{ value: "days", label: "дольше идут" }, { value: "rank", label: "по показам" },
          { value: "copies", label: "больше копий" }, { value: "fresh", label: "новые" }], "days", reset("sort"))),
      count, grid, more);
    draw();
  }

  function kv(pairs) {
    return h("dl", { class: "kv wide" }, pairs.filter((p) => p[1] !== null && p[1] !== "" && p[1] !== undefined)
      .map(([k, v]) => [h("dt", {}, k), h("dd", {}, v)]));
  }

  function tagBlock(t) {
    if (!t) return h("p", { class: "small muted" }, "Этот креатив не попал в выборку для ручной разметки — ниже только автоматические данные.");
    return kv([
      ["Хук", h("span", {}, h("q", {}, t.hook), " ", h("span", { class: "chips" }, t.hook_types.map((x) => chip(x))))],
      ["Визуал хука", t.visual.length ? h("span", { class: "chips" }, t.visual.map((x) => chip(x))) : null],
      ["Смысл", h("span", { class: "chips" }, t.meaning.map((x) => chip(x)))],
      ["Обещание дохода", t.income_claim ? h("span", {}, h("q", {}, t.income_claim), " — заявление школы") : null],
      ["Оффер", h("span", { class: "chips" }, t.offer.map((x) => chip(x)))],
      ["Цена в креативе", t.price_quote ? h("q", {}, t.price_quote) : null],
      ["Призыв", [t.cta_in_creative, t.destination, t.funnel_stage].filter(Boolean).join(" → ")],
      ["Спикер", [t.speaker, t.speaker_name].filter(Boolean).join(": ")],
      ["Стиль", t.style.join(", ")],
      ["Язык", t.language],
      ["Риск", t.risk ? chip("нереалистичные обещания или трейдинг", "risk") : null],
      ["Уверенность разметки", t.confidence],
      ["Заметки", t.notes || null],
    ]);
  }

  function openCreative(id) {
    const c = byId[id];
    if (!c) return;
    const dialog = document.getElementById("creative-dialog");
    const src = thumbOf(c);
    const transcript = c.transcript
      ? h("div", { class: "col" }, h("h4", { class: "filter-label" }, "Расшифровка речи (черновая, mlx-whisper)"), h("pre", {}, c.transcript))
      : h("p", { class: "small muted" }, c.transcript_quality ? `Расшифровка не показана: качество «${c.transcript_quality}».` : "Расшифровки нет (картинка или видео не скачалось).");
    dialog.replaceChildren(
      h("div", { class: "detail-head" },
        h("h3", {}, `${schoolName[c.school]} · ${FORMAT_LABEL[c.format] || c.format} · ${fmt(c.days)} дн.`),
        h("button", { type: "button", class: "more", onclick: () => dialog.close() }, "Закрыть")),
      h("div", { class: "detail-body" },
        h("div", { class: "col" },
          src ? h("img", { src, alt: "Кадр креатива" }) : h("div", { class: "ph small muted" }, "нет превью"),
          link(c.ad_url, "Объявление в библиотеке Meta"),
          c.link ? link(c.link, "Куда ведёт ссылка") : null,
          h("p", { class: "small muted mono" }, c.media_folder)),
        h("div", { class: "col" },
          kv([
            ["Запущен", c.first_started], ["Идёт", h("span", {}, tierMark(c.tier), ` ${fmt(c.days)} дн.`)],
            ["Объявлений", c.ads > 1 ? `${c.ads} (перезапусков по датам: ${c.relaunches})` : "1"],
            ["Место по показам", c.rank ? `№${c.rank} из первых 30` : null],
            ["Кнопка", c.cta], ["Куда ведёт", c.destination], ["Платформы", c.platforms],
            ["Почему в разметке", c.selected_because || null],
          ]),
          tagBlock(c.tags),
          h("h4", { class: "filter-label" }, "Текст объявления"),
          h("pre", {}, c.text || "без текста"),
          transcript)));
    if (!src) loadData("thumbs", c.school).then(() => { const s = thumbOf(c); if (s) dialog.querySelector(".detail-body .col").prepend(h("img", { src: s, alt: "Кадр креатива" })); });
    dialog.showModal();
  }

  document.addEventListener("click", (e) => {
    const dialog = document.getElementById("creative-dialog");
    if (e.target === dialog) dialog.close();
  });

  window.Gallery = { mountGallery, openCreative, card, fillThumbs, byId };
})();
