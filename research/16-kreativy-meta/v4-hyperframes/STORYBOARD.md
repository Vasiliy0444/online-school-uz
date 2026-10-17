# STORYBOARD — V4 «Bu rolikni AI yaratdi» (HyperFrames)

Холст 1080×1920, 30 fps, 32,5 с, 120 BPM (доля 0,5 с). Время — только из `timeline.json` (его же читает звук).
Все узбекские строки — из `../montage-remotion/src/montage/text.ts`, новых формулировок нет.

**Мотив.** Светящаяся синяя точка. Каждое утверждение заканчивается ею. Переходы «зум сквозь» ныряют в точку уходящей сцены и выходят из точки новой (S2→S3→S4→S5→S6).
В S4 точка — головка плейхеда, в S5 — кончик графика, в финале — стрелка вниз.

**Палитра.**
- фон ink `#0B0A12`, свет комнаты фиолетовый/янтарный/синий;
- белый `#F5F4FA`;
- акцент `#7C95FF` со свечением `#4D6BFF`;
- жёлтый `#FFD23F` придержан: полоски чипов и стена-флёрри;
- зелёный `#2ED47A` — галочки, красный `#FF3D5A` — зачёркивания и REC.

**Шрифты.** Montserrat 700/900 — весь текст; JetBrains Mono 700 — HUD и чипы. Оба встроены в HyperFrames.

**Безопасная зона.** Смысловой текст — y 270–1248, x 65–1015. HUD декоративный, стоит выше и ниже зоны.

**Переходы.**
- основной — zoom-through ×4, с центром в точке; старая сцена гаснет за 0,3 с, новая входит с T+0,25 (после аудита: текст сцен не накладывается);
- акценты — chromatic glitch ×2, clone wall (флёрри), overexposure ×1 (только белый слой, пик 0,8).

**HUD (motion-showreel).**
- уголки кадра по краям безопасной зоны, вспыхивают на каждой склейке;
- REC мигает в долю, таймкод, линейка прогресса с 8 главами, `1080×1920 · 30P · 120 BPM`.

## Frame 1
status: outline
src: index.html#s1
blueprint: kinetic-type-beats
rules: chromatic-glitch, kinetic-beat-slam
beat: 0,0 «Bu rolikni» по дуге видна с первого кадра: RGB-разъезд гаснет за 0,3 с, сигнал «ловится». 0,5 «AI» — удар (масштаб и размытие, тряска, RGB-вспышка). 1,0 «yaratdi» влетает справа. 1,25 синяя точка. 1,75 вторая глитч-вспышка «AI».

## Frame 2
status: outline
src: index.html#s2
blueprint: grid-card-assemble
rules: spring-pop-entrance, kinetic-beat-slam
beat: 2,5 вход глитчем. 2,55 семь карточек с настоящими сайтами раскрываются веером от центра: fbstore, synapt, racescout, mrktcorrect (в центре), automyai, oreshkinmedialab, ondrejmachart. Переменная `fbstore=off` даёт вариант из 6 карточек. Ценники «$100» на верхнем слое. Субтитр по словам в восьмые доли: «Bunaqasini mijozlarga» / «$100 dan sotamiz». На слове «$100» (3,5) каскадом через 0,08 с всплывают ценники $100. 4,25 точка. 4,75 блик по вееру. 5,25 наезд камеры.

## Frame 3
status: outline
src: index.html#s3
blueprint: kinetic-type-beats
rules: waterfall-entry, svg-path-draw, ambient-glow-bloom
beat: 6,0 зум сквозь точку. «Dizayn, montaj va dasturlashni» по словам с 6,25 (чип TOP-3 убран после аудита: по смыслу не подходил). 6,75 «BILMASDAN» — удар, 7,0 «QILAMIZ» влетает сбоку, 7,25 точка. Строки 01–03 (dizayn, montaj, dasturlash) на долях 7,5 / 8,0 / 8,5. Через 0,25 с после каждой — красное зачёркивание. 9,25 свечение ключевой фразы.

## Frame 4
status: outline
src: index.html#s4
blueprint: agent-progress-theater
rules: stat-bars-and-fills, discrete-text-sequence
beat: 10,0 зум из точки в головку плейхеда. «Bitta rolikka —» (10,25) / «ikki soatcha» (10,5). Минутная стрелка часов делает 2 оборота (два часа). Панель AI-MONTAJ: кадры V1 заполняются сами, волна A1 открывается за плейхедом. Плашки SFX — Whoosh, Pop, Riser, Glitch, Zoom — встают в восьмые доли, и каждая звучит своим звуком.

## Frame 5
status: outline
src: index.html#s5
blueprint: kinetic-type-beats
rules: counting-dynamic-scale, svg-path-draw
beat: 13,5 зум из конца плейхеда в начало графика. Стеклянная карточка «Hisob-kitob, va’da emas». Счёт $100 → $1000 идёт с 14,0 десятью ступенями по 0,2 с, лесенка графика рисуется синхронно, искра бежит по её кончику. Вопрос «Siz ham onlayn AI-mutaxassis kasbini egallab,» идёт по словам. 15,875 «$1000 ga chiqmoqchimisiz?» бьёт сразу после того, как счёт дошёл до $1000. 16,125 чип «10 × $100». С 16,25 медленный наезд камеры до конца сцены: пауза без движения была 2,2 с.

## Frame 6
status: outline
src: index.html#s6
blueprint: agent-progress-theater
rules: kinetic-beat-slam, svg-path-draw (success-check)
beat: 18,5 зум из искры в точку. 18,75 «Bepul» — удар, 19,0 «mini-kurs» поднимается с поворотом, 19,25 точка. Три галочки на долях 19,5 / 20,0 / 20,5: mutlaqo noldan, dasturlashni bilmasdan, sarmoyasiz.

## Frame 7
status: outline
src: index.html#s7
blueprint: grid-card-assemble
rules: waterfall-entry, kinetic-beat-slam
beat: 21,5 вход глитчем. Чип KUN OXIRIGACHA. Двенадцать плиток BEPUL в 12 стилях падают каскадом через 0,06 с. 22,75 «0 so‘m» — главный удар ролика (импакт, тряска). 23,25 «Keyin — 3 mln so‘m». 24,25 волна подсветки по плиткам.

## Frame 7b
status: outline
src: index.html#cw
blueprint: — (registry block mk-clone-wall-transition, адаптирован под 9:16)
rules: motion-showreel flurry
beat: 25,0 кадр S7 сжимается в карточку, за ним жёлтая стена BEPUL, ряды едут навстречу. 25,5 карточка улетает вверх. 25,75 инверсия цвета шторкой. 26,0 стена ускоряется. 26,25 пересвет белым слоем до 0,8, 26,45 смена сцены.

## Frame 8
status: outline
src: index.html#s8
blueprint: kinetic-type-beats
rules: kinetic-beat-slam, waterfall-entry
beat: 26,5 выход из пересвета. «Pastdagi tugmani bosing» / «va bepul kursni ko‘ring» по словам в восьмые. 28,375 карточка «Bepul mini-kurs · Onlayn AI-mutaxassis kasbi» со значком-искрой. 29,0 «BOSING» — удар, нижний HUD гаснет. 29,25 три шеврона вниз, по ним до последнего кадра бежит волна света в восьмые — к настоящей кнопке Meta под видео. Нарисованной кнопки и курсора нет: правило Meta о несуществующих функциях (см. МОДЕРАЦИЯ-V4.md).
