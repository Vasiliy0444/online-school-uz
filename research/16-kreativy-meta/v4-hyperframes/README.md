# V4 — монтаж «Bu rolikni AI yaratdi» на HyperFrames

Переделка V3 (Remotion, `../montage-remotion`) после установки 15 репозиториев моушн-дизайна (11.10.2026).
Без Никиты. Его аватар — следующая итерация, задача CURSOR-seqv.

## Что внутри

| Файл | Зачем |
|---|---|
| `index.html` | композиция: 8 сцен, HUD, переходы, один таймлайн GSAP |
| `timeline.json` | все времена ролика; его читают и картинка, и звук |
| `sync_timeline.py` | вставляет `timeline.json` в `index.html` (маркеры `TL-BEGIN/TL-END`) |
| `sfx-cues/v4.py` | партитура звука для движка sound-design (whaleyxbt/claude-motion) |
| `assets/audio/v4_sfx.wav` | готовый звук: −14 LUFS, true peak −2,5 dBFS (в MP4 после AAC −2,2) |
| `assets/grain.png` | зерно, сгенерировано с фиксированным seed |
| `BRIEF.md`, `STORYBOARD.md` | бриф и раскадровка по сценам со ссылками на приёмы |
| `compositions/` | блоки и компоненты из реестра HyperFrames; их приёмы встроены в `index.html` |
| `renders/` | финал `V4_final_story.mp4` (9:16), `V4_final_feed_4x5.mp4`, вариант без fbstore `V4b_bez_fbstore_*`, сравнение с V3, аудит `АУДИТ-V4.md` |
| `assets/sites/` | скрины сайтов для сцены 2 (исходники 1170×1992 — `../assets/sites/`) |
| `МОДЕРАЦИЯ-V4.md` | проверка рисков модерации Meta и что исправлено |

## Чем собрано

- Сборка и проверка — **HyperFrames** (heygen, CLI 0.8.147): `lint`, `check` (раскладка, контраст, движение), `snapshot`, `render`.
- Движение — правила из `hyperframes-animation`:
  - zoom-through: камера ныряет в синюю точку;
  - chromatic-glitch;
  - kinetic-beat-slam;
  - counting-dynamic-scale: $100 → $1000 ступенями синхронно с лесенкой;
  - svg-path-draw;
  - waterfall-entry: шевроны вниз к настоящей кнопке Meta под видео.
- Флёрри перед призывом — блок реестра `mk-clone-wall-transition`, переделанный под 9:16: стена BEPUL, инверсия, пересвет.
- HUD, главы, склейки в сетке 120 BPM, придержанный жёлтый — грамматика `motion-showreel`.
- Вкус — `whaley-motion-design`: точки отсчёта в одном `timeline.json`, удержания для чтения, один акцент, один главный удар («0 so‘m»).
- Звук — `sound-design`: процедурные звуки без чужой музыки, бочка в долю, у каждой плашки SFX свой звук.

## Как пересобрать

```bash
python3 sync_timeline.py
```

```bash
cd ~/.claude/motion-repos/whaleyxbt_claude-motion && python3 -m sfx "$OLDPWD/sfx-cues/v4.py" --timeline "$OLDPWD/timeline.json" --out "$OLDPWD/assets/audio/v4_sfx.wav"
```

```bash
npx hyperframes check
```

```bash
npx hyperframes render -q delivery -w 4 -o renders/V4_final_story.mp4
```

Вариант без fbstore.shop на сцене 2 (переменная композиции `fbstore`):

```bash
npx hyperframes render -q delivery -w 4 --variables '{"fbstore":"off"}' -o renders/V4b_bez_fbstore_story.mp4
```

Лента 4:5 — кроп `crop=1080:1350:0:84` из 9:16: смысловой текст стоит в полосе 270–1248 px и целиком попадает в кадр.
