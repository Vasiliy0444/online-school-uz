# Тексты под постами UZ, пулы 7–9: правки редактора, v1 → v2

**Итог.** Внесено 7 замен в 5 текстах из 9, по смыслу это 5 решений. Пул 9 и P8 short не тронуты.
- Главное по тону: в P8 «aql bilan» («головой») заменено на «bilim bilan» («знаниями»), чтобы фраза не задевала тех, чьи родные работают за границей. Хвост P8 long приведён к формулировке карусели 2-4: «oila yoningizda».
- Главное по языку: в P7 «pulni esa … ishlaydi» стало «pulni esa …larga to‘lashadi» («платят тем»), а «умеют» теперь везде «biladi».
- Живому носителю в первую очередь: «chetga ishlagani ketadi», тон «Bilak kuchi bilan emas, bilim bilan», хук P9 с «va’da».

Вычитку делал ИИ (Claude) в роли носителя, перевод тоже делал ИИ. Перед запуском нужен живой носитель.
Корпус для чисел ниже: `../03-reklama-meta/ads_uz_info.csv`, строки `is_uzbek=True`, 532 уникальных текста. Апострофы перед поиском сведены к одному знаку, регистр не учитывался. «Текстов» значит уникальные тексты `body`.

---

## Правки: пул · длина · было → стало · почему

### 1. P8 · mid, long · «aql bilan» → «bilim bilan»
- **Было:** «Bilak kuchi bilan emas, **aql** bilan ishlaysiz.»
- **Стало:** «Bilak kuchi bilan emas, **bilim** bilan ishlaysiz.»
- **Почему:**
  - Противопоставление «руками, а не умом» намекает, что тот, кто работает руками, не работает головой. «aql» («ум») — врождённое качество, поэтому для семьи, где кто-то уехал на заработки, это прямой укол. «bilim» («знания») приобретают, и курс их как раз даёт. Обиды нет.
  - «bilak kuchi» оставлено: оборот уважительный, так говорят о честном труде («bilak kuchi bilan non topadi»).
  - Связка «bilak — bilim» отсылает к пословице «Bilagi zo‘r birni yiqar, bilimi zo‘r — mingni»: знание ставят выше силы, но силу не принижают.
  - В корпусе так и делают: противопоставляют тяжёлую работу знаниям, никого не оценивая. [Smarthub](https://www.facebook.com/ads/library/?id=1609298507478618): «Pul topish uchun har kuni og‘ir ishlash shart deb o‘ylaysizmi?», [Smarthub](https://www.facebook.com/ads/library/?id=1314584507208071): «o‘rgangan bilimlaringiz orqali uydan turib … online ishlash».
  - Цифры: «bilim» — 84 текста у 56 рекламодателей; «aql» — 0, единственное совпадение — название шоу AQLTOY; «bilak» — 0.
- **Сдвиг смысла:** «головой» → «знаниями». Мысль «умственный труд вместо физического» сохранена.

### 2. P8 · long · «oilangiz yonida qolasiz» → «oila yoningizda qoladi»
- **Было:** «… ishlaysiz — va **oilangiz yonida qolasiz**.»
- **Стало:** «… ishlaysiz — va **oila yoningizda qoladi**.»
- **Почему:**
  - Это формулировка карусели 2-4 этого пула: «Oila yoningizda» стоит в подзаголовке и на карточке 2. Подпись и картинка теперь говорят одинаково.
  - В хуке переводчик сознательно не писал «oilangiz», чтобы не утверждать, что у читателя есть семья. Хвост long это правило нарушал.
  - Получилась перекличка с той же фразой выше: «oila esa uzoqda qoladi» → «oila yoningizda qoladi». В русском то же самое: «семья остаётся далеко» → «остаёшься с семьёй».
- **Оговорка:** «oilangiz» в рекламе встречается, например у [Smarthub](https://www.facebook.com/ads/library/?id=1047475578160800): «Oilangizga ko‘proq vaqt ajratmoqchi bo‘lsangiz». Правка ради совпадения с картинкой, а не из-за запрета.

### 3. P8 · mid, long · «uning bir qismini yeb ketadi» → «bir qismi … ga ketadi»
- **Было:** «U yerda boshida daromad ko‘proq, lekin **patent, ijara va ovqat uning bir qismini yeb ketadi**, oila esa uzoqda qoladi.»
- **Стало:** «U yerda boshida daromad ko‘proq, lekin **bir qismi patent, ijara va ovqatga ketadi**, oila esa uzoqda qoladi.»
- **Почему:**
  - «uning» про неодушевлённое «daromad» в той же фразе звучит как перевод: по-узбекски хватает притяжательного «-i».
  - Про расходы в быту говорят «…ga ketadi» («уходит на…»). Это запасной вариант самого переводчика (сомнение 8).
  - «yeb» в корпусе — 0.
  - Образ «съедают» смягчился. Для чувствительной темы это плюс: меньше драмы, факт тот же — часть заработка уходит на патент, жильё и еду.
- «daromad» и «ijara» (как на карусели) оставлены.

### 4. P7 · short, mid, long · «умеют» → «biladi»
- **Было:** «Qila oladiganlar ko‘p…», «Sayt va bot yasay oladiganlar ko‘p.», «Sayt yoki bot yasay oladiganlar ko‘p.»
- **Стало:** «**Qilishni biladiganlar** ko‘p…», «Sayt va bot **yasashni biladiganlar** ko‘p.», «Sayt yoki bot **yasashni biladiganlar** ko‘p.»
- **Почему:**
  - Русское «умеют» передаётся через «bilmoq», а «qila olmoq» значит «могут». Это правило уже применено в I3-3 («topishni bilmaysizmi») и в прошлой вычитке (`pools_uz_v2_pravki.md`, правка 8).
  - В этом же тексте хук спрашивает «Mijoz topishni bilmaysizmi?». Теперь вторая фраза отвечает тем же глаголом: делать умеют многие, а находить клиентов — нет.
  - Корпус: «biladiganlar» — 1 текст, [Logist Academy](https://www.facebook.com/ads/library/?id=2225728551508423): «ingliz tilini biladiganlarga emas»; «oladiganlar» — 0.

### 5. P7 · short, mid, long · «pulni … ishlaydi» → «pulni …larga to‘lashadi»
- **Было:** «pulni esa mijoz topadiganlar **ishlaydi**», «Pulni esa mijoz topib, munosib narx so‘raydiganlar **ishlaydi**.» (mid и long)
- **Стало:** «pulni esa mijoz **topadiganlarga to‘lashadi**», «Pulni esa mijoz topib, munosib narx **so‘raydiganlarga to‘lashadi**.»
- **Почему:**
  - «pul ishlamoq» — устойчивое сочетание, оно не берёт винительный падеж. «Pulni … ishlaydi» режет слух.
  - Русское «платят тем, кто…» — это дословно «…larga to‘lashadi».
  - Безличное 3-е лицо множественного числа уже стоит в пулах 1–6: «to‘lashsa», «to‘lashlarini», «sotishadi».
  - Страдательный вариант переводчика («pul … to‘lanadi») не взял: книжно.
  - В корпусе «to‘lashadi» — 0, решение по норме языка. Корпус про оплату почти молчит: «to‘lash» встречается только в «bo‘lib to‘lash» (рассрочка).
- **Побочный эффект в P7 long:** следующая фраза тоже с этим глаголом («qancha to‘lashsa, shunga olasiz»). Получается перекличка: платят тем, кто…, а пока вы берёте, сколько дадут. Оставил.

---

## Сомнения переводчика, которые я не трогал

| № в v1 | Где | Решение | Почему |
|---|---|---|---|
| 1 | P8, хук | «chetga ishlagani ketadi» оставлено | Дословно как на карусели 2-4. Без оценки, третье лицо. Корпус спор не решает: «chetga» и «ishlagani» — 0; «chet el» — 4 текста, все про учёбу ([British Council](https://www.facebook.com/ads/library/?id=1315735900625890)); «mardikor», «musofir», «migrant» — 0. «chet elga» однозначнее, но менять можно только вместе с каруселью |
| 4 | P9, хук | «va’dasimi» оставлено | Без существительного вопрос получается «Yana «AI orqali $1000»mi?»: орфографически верно, но аффикс после кавычки на экране спотыкается. Вариант «degan gapmi» повторит «gap» в соседней фразе. Новых фактов «va’da» не добавляет, это ярлык чужой рекламы. Так пишут и скептики в корпусе: «va’da» — 3 текста, [Hirex](https://www.facebook.com/ads/library/?id=1258670336344494): «Quruq va’dalar emas», [Kosmedia.uz](https://www.facebook.com/ads/library/?id=27873549662341793): «havoyi va’dalar bermaydi». Риск остаётся: слово подсвечивает, что $1000 — обещание, а наш курс тоже про $1000. Вопрос носителю № 3 |
| 5 | P9 | «Quruq gapga ishonmang» оставлено | «quruq» в смысле «пустой» — [Hirex](https://www.facebook.com/ads/library/?id=1258670336344494): «Quruq va’dalar», [TOPEX](https://www.facebook.com/ads/library/?id=946171537830567): «quruq nazariya». Оттенок чуть резче русского «не верь на слово»: слова чужой рекламы названы пустыми. Смысл «слова против доказательства» тот же |
| 6 | P9 mid, long | «Kod yozmadim: … berdim, bajardi, tekshirdim» оставлено | Русская подпись — «без программирования», а не «без знаний» (как на I3-2), поэтому «kod yozmadim» точнее. Простое прошедшее короче и повторяет схему P2 |
| 7 | P7, хук | «Xizmatingizni arzonga sotasizmi?» оставлено | Совпадает с заголовком I3-3. «arzonga sotmoq» — бытовое, корпус: «arzon» — 5 текстов, например [Glamour shop](https://www.facebook.com/ads/library/?id=2212655786234609): «ARZON NARXDA». Не оскорбление: вопрос про цену услуги, а не про человека |
| 3 | P8 mid, long | «Uyda ham mijozlar bor» оставлено | Это пара к меткам карусели «U yerda / Uyda». После двоеточия сразу идёт «shahringizdagi…», и смысл «на родине» понятен. Но в корпусе «uyda» — 4 текста, и все в смысле «в доме» ([Logist Academy](https://www.facebook.com/ads/library/?id=1028649392822461): «🏠 uyda»). Вопрос носителю № 4 |
| 9 | P8, хук | «…pul ishlashning iloji bormi?» оставлено | Норма. Разговорнее было бы «…pul ishlasa bo‘ladimi?», как у [Yulduz Shardemetova](https://www.facebook.com/ads/library/?id=1052083560932334): «Hali olsa bo‘ladimi?». Оба естественны, правка была бы вкусовой |
| 10 | P7 mid, long | «munosib narx» оставлено | «munosib» — 2 текста, [Logist Academy](https://www.facebook.com/ads/library/?id=2212299902842947): «munosib daromad topishni». «normal narx» — 0, и это русизм |
| 12 | P7 mid, long | «birjasiz» оставлено | Так на карусели 2-3: «Birjasiz mijoz qayerdan topiladi». «birja» — 0, «frilans» — 2 текста |
| 13 | P7 long | «beqaror» оставлено | Антоним «barqaror» в рекламе живой (14 текстов), «beqaror» — 0, но слово обиходное |
| 14 | P7 long | «— narxingiz uchun mo‘ljal shu» оставлено | Тот же образ, что в русском «ориентир». В корпусе 14 текстов, но только «mo‘ljallangan» и адресное «Mo‘ljal: …», например у [Iskandar Sattiboyev](https://www.facebook.com/ads/library/?id=2419271085147600). Риск низкий. Запасной вариант: «— narxingizni shunga qarab qo‘yasiz» |
| 15 | P8 mid, long | «uyingizga yaqin» оставлено | Русский в P8 другой («рядом с домом», а не «в своём районе»), поэтому формула пулов 1–6 не обязательна. Модель — [Sodiq School](https://www.facebook.com/ads/library/?id=2027023727947595): «Uyingizga yaqin joyda» |

Сомнения 2, 8 и 11 закрыты правками 1, 3 и 5.

**Новое наблюдение.** В корпусе вопрос «не умеете?» чаще задают в продолженной форме: «bilmayapsizmi» — 8 текстов, «bilmaysizmi» — 2. Пример — [Aziz Djamolov](https://www.facebook.com/ads/library/?id=27697016846614369): «Ishni nimadan boshlashni bilmayapsizmi?». У нас «bilmaysizmi» стоит в хуке P7, на картинке I3-3 и в пуле 5. Не менял: если менять, то во всех трёх местах сразу.

---

## Единообразие с пулами 1–6 — проверено скриптом

- Строки, где русский совпадает с пулами 1–6, совпадают и по-узбекски, все 16. Это оба призыва с ⏳ и 👆, буллеты про 5 услуг, план на $1000 и топ-10 каналов.
- Дословно совпадают и фразы внутри строк:
  - «3 mln o‘rniga 0 so‘m — faqat kun oxirigacha…»;
  - «Birinchi dars bilan birga — bonus…»;
  - «Toshkentdagi studiyalar…»;
  - «Telegramdagi bepul mini-kursda — darslar va amaliyot:»;
  - название курса;
  - «kod yozish shart emas»;
  - «yaqin atrofingizdagi 3 ta kompaniyani topib, ularga sayt yasaysiz».
- Сколько раз стоят термины в 9 текстах:
  - «Batafsil» — 9;
  - mini-kurs — 9;
  - kun oxirigacha — 9;
  - yaqin atrofingizdagi — 4;
  - AI — 11;
  - neyrotarmoq — 0.
- «AI-mutaxassis» в русских текстах 7–9 нет, поэтому нет и в переводе.

## Как проверено

- `python3 check_uz.py <scratchpad>/p_merge_check.json`: пулы 1–6 из `pools_uz_final.json` плюс 7–9 из v2. Результат: **ошибок 0, предупреждений 0**. Рост длины в среднем 1,13, максимум 1,21 (P9 short, не менялся).
- Орфография в 7–9:
  - ‘ (U+2018) — 73, все после o/g;
  - тутук ’ — 3, это «va’dasimi» в P9;
  - ASCII-апострофы, ʻ, кириллица, «sen», двойные пробелы — 0.
- Слов-обещаний («kafolat», «tez», «oson pul», «passiv daromad») — 0. Числа, эмодзи и их порядок, абзацы и строки не тронуты.

---

## Вопросы живому носителю (по убыванию риска)

1. **P8, хук: «Ko‘p odam chetga ishlagani ketadi».** Звучит ли нейтрально, без жалости и оценки? «chetga» или «chet elga»? Если менять, то вместе с каруселью 2-4.
2. **P8 mid, long: «Bilak kuchi bilan emas, bilim bilan ishlaysiz».** Не обидно ли тем, у кого родные на заработках? Естественно ли «bilim bilan ishlash»? Для сравнения: в v1 было «aql bilan».
3. **P9, хук: «Yana «AI orqali $1000» va’dasimi? Quruq gapga ishonmang».** Не бьёт ли «va’da» по нашему же курсу про $1000? Не слишком ли резко «quruq gap»? Альтернатива: «Yana «AI orqali $1000»mi?».
4. **P8: «Uyda ham mijozlar bor».** Читается как «на родине тоже есть клиенты» или как «в доме»? Альтернатива: «O‘zimizda ham mijozlar bor».
5. **P7: «pulni esa mijoz topadiganlarga to‘lashadi».** Естественно ли? Для сравнения: в v1 было «pulni esa … ishlaydi».
6. **P7, хук: «Xizmatingizni arzonga sotasizmi?»** Не звучит ли упрёком? Менять только вместе с I3-3. Заодно: «bilmaysizmi» или «bilmayapsizmi»?
7. **P8 long: «— va oila yoningizda qoladi».** Естественно ли рядом с «oila esa uzoqda qoladi»?
8. **Мелочи:** «mo‘ljal shu» (P7 long), «beqaror» (P7 long), «munosib narx» (P7), «Kod yozmadim» (P9).
9. **Унаследовано от пулов 1–6, касается и этих текстов:**
   - кнопка «Batafsil» — 9 раз;
   - AI в роли подлежащего — P9 «AI bajardi»;
   - «yaqin atrofingizdagi» — 4 раза.
