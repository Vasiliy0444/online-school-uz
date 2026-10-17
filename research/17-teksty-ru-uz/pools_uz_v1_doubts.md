# Тексты под постами UZ v1 — что проверить живому носителю

Файл перевода: `pools_uz_v1.json` (6 пулов × 3 длины = 18 текстов). Перевод сделал ИИ (Claude) в роли копирайтера из Ташкента. Перед запуском нужна вычитка живым носителем.

Корпус — `../03-reklama-meta/ads_uz_info.csv`, 832 объявления с `is_uzbek=True`. Ниже «0 в корпусе» значит, что конкуренты так не пишут. Это ещё не значит, что так писать нельзя.

---

## Сомнения: от самого рискованного

### 1. Кнопка «Batafsil» — ⚠️ место под замену

- **Где:** 17 из 18 текстов, в каждом CTA: ««Batafsil» tugmasini bosib, ro‘yxatdan o‘ting», ««Batafsil» tugmasini bosing va boshlang» и т. п. Кнопки нет только в P1 short.
- **Почему сомневаюсь:**
  - Конкуренты в узбекских текстах называют кнопку по-русски, кириллицей: «Подробнее» встречается в 17 объявлениях. Примеры: [Ozoda Fashion Academy](https://www.facebook.com/ads/library/?id=1600580618382943) — «quyidagi «Подробнее» tugmasini bosib ro’yxatdan o’ting», [Blitz](https://www.facebook.com/ads/library/?id=1573174234317319), [Hojimurod Bakirov](https://www.facebook.com/ads/library/?id=1101117128957349). [Iteach](https://www.facebook.com/ads/library/?id=1129400022747763) пишет оба варианта: «“Подробнее” yoki “Learn more” tugmasini bosing».
  - «Batafsil» как название кнопки — 0 в корпусе. Слово встречается только в обороте «batafsil ma’lumot».
  - Не проверено, как кнопка «Подробнее» подписана в узбекском интерфейсе Instagram и Facebook и есть ли он у Instagram вообще. Если у зрителя русский интерфейс, он увидит «Подробнее», а текст отправит его искать «Batafsil».
- **Запасные варианты:**
  - A, нейтральный, подходит к интерфейсу на любом языке: «👆 Ro‘yxatdan o‘tish uchun yuqoridagi tugmani bosing.» Модель — [Edupro.uz](https://www.facebook.com/ads/library/?id=1052426477455494): «👆 Darsni olish uchun yuqoridagi tugmani bosing».
  - B, как у конкурентов: ««Подробнее» tugmasini bosib, ro‘yxatdan o‘ting». Ломает правило «без кириллицы», решает Вася.
- Заменять в JSON одной операцией: строка ««Batafsil»» встречается ровно 17 раз.

### 2. «neyrotarmoq» вместо русского «нейросеть»

- **Где:** во всех пулах, 19 раз: «Asosiy ishni neyrotarmoq qiladi», «neyrotarmoq bilan qilinadigan 5 ta xizmat», «neyrotarmoqlar bepul».
- **Почему сомневаюсь:** это литературный термин. В корпусе он есть в 3 объявлениях: [Sfera academy](https://www.facebook.com/ads/library/?id=1092976069799567), [Smmikramovna](https://www.facebook.com/ads/library/?id=1733681401255548), [furkatovna.smm](https://www.facebook.com/ads/library/?id=1057114310531276). «AI» встречается в 38 объявлениях (глоссарий `creatives_uz.json`). Разговорное «neyroset» — 0. Оставил «neyrotarmoq», чтобы сохранить разницу между русскими «ИИ» и «нейросеть» и совпасть с каруселью 2-1 («neyrotarmoqlar bepul»). Но молодёжи 18–30 текст может показаться книжным.
- **Запасной вариант:** везде «AI»: «Asosiy ishni AI qiladi», «AI bilan qilinadigan 5 ta xizmat». Разница ИИ/нейросеть пропадёт, но по смыслу это одно и то же.

### 3. Хук пула 2: «Vaqtingizni arzimagan pulga sotyapsizmi?»

- **Где:** P2, все три длины, первая строка.
- **Почему сомневаюсь:** «за копейки» = «arzimagan pulga» («за ничтожные деньги»). Грамматика верная, но в корпусе 0. Если звучит книжно, хук теряет силу.
- **Запасные варианты:**
  - «Vaqtingizni arzonga sotyapsizmi?» — как «Xizmatingizni arzonga sotasizmi?» в креативе I3-3. Слабее: «дёшево» вместо «за копейки».
  - «Vaqtingizni tiyinga sotyapsizmi?» — разговорнее, но «tiyin» может показаться устаревшим.

### 4. «Vaqtingizni sotishni bas qiling — natijani soting.»

- **Где:** P1 mid и P1 long, второй абзац.
- **Почему сомневаюсь:** «bas qiling» = «хватит, перестаньте». В обороте «…ni bas qiling» это норма («chekishni bas qiling»), но отдельно «Bas qiling!» звучит как окрик. В корпусе 0.
- **Запасной вариант:** «Vaqtingizni emas, natijani soting.» Так уже стоит в P3 short, а в креативе I2-3 — «Vaqtingizni emas, tayyor natijani sotishni o‘rganish kerak». Пропадёт оттенок «перестань».

### 5. «tumaningizdagi 3 ta kompaniya» — «в своём районе»

- **Где:** во всех длинных текстах и в буллете «на практике находишь 3 компании…».
- **Почему сомневаюсь:** «tuman» — административный район. В Ташкенте это нормально, а в области tuman большой, на десятки сёл. Русское «в своём районе» в разговоре скорее значит «рядом, по соседству». В корпусе 0.
- **Запасные варианты:** «yaqiningizdagi 3 ta kompaniya» («рядом с вами»), «atrofingizdagi» («вокруг вас»), «mahallangizdagi» — по-моему, слишком мелко для 3 компаний.

### 6. «Talaba bo‘lsangiz…» — хук P1 mid

- **Полная фраза:** «Talaba bo‘lsangiz va internetda hali bir marta ham pul ishlamagan bo‘lsangiz, oyiga $1000 ga qanday chiqasiz?»
- **Почему сомневаюсь:**
  - Дословное «O‘qisangiz» («если учишься») отбросил: «o‘qimoq» — это ещё и «читать», в подписи к посту «O‘qisangiz…» читается как «если прочитаете».
  - «Talaba» — только студент вуза, школьников и колледж оно не охватывает.
  - Два «bo‘lsangiz» подряд тяжеловаты.
- **Запасные варианты:**
  - «Hali o‘qiyotgan bo‘lsangiz va internetda bir marta ham pul ishlamagan bo‘lsangiz, oyiga $1000 ga qanday chiqasiz?»
  - Короче, утверждением: «O‘qiyapsiz, internetda hali bir marta ham pul ishlamagansiz — oyiga $1000 ga qanday chiqasiz?»

### 7. «biznes ijrochi qidiradigan top-10 kanal»

- **Где:** P5 mid и P5 long, бонус «топ-10 каналов, где бизнес ищет исполнителей».
- **Почему сомневаюсь:** «ijrochi» в паре «buyurtmachi — ijrochi» значит «исполнитель заказа», но в обиходе это прежде всего «исполнитель песен». В корпусе 0.
- **Запасные варианты:** «biznes mutaxassis qidiradigan top-10 kanal» или «biznes frilanser qidiradigan top-10 kanal».

### 8. «Kun oxirigacha kurs bepul ochiq.»

- **Где:** P2 и P3, во всех трёх длинах, — «до конца дня курс открыт бесплатно».
- **Почему сомневаюсь:** у конкурентов «ochiq» почти всегда стоит в «bepul ochiq dars» («открытый урок»). «Kurs bepul ochiq» понятно, но может звучать как сдвинутый термин.
- **Запасной вариант:** «Kun oxirigacha kurs bepul.» Короче, срочность сохранена.

### 9. «Aksiya davom etar ekan, kurs to‘liq bepul.»

- **Где:** P1 mid — «Пока действует предложение, курс полностью бесплатный».
- **Почему сомневаюсь (риск небольшой):** «aksiya» — это и «промо», и «акции компаний». В корпусе 9 объявлений со словом:
  - в 6 — «промо», в том числе у курсов: [7edu](https://www.facebook.com/ads/library/?id=3093712464157730) — «1+1 AKSIYA», [Muattar Shuhratovna](https://www.facebook.com/ads/library/?id=1410368317660173) — «AKSIYA ONLAYN KURS», [Asakabank](https://www.facebook.com/ads/library/?id=1103927438742247) — «Aksiya … davom etadi»;
  - в 3 — «акции», все три у [Uznetix](https://www.facebook.com/ads/library/?id=1687841545835931) (реклама инвестиций).

  В тексте про заработок второе прочтение возможно, но рядом стоит «kurs to‘liq bepul», и оно снимается.
- **Запасной вариант:** «Taklif amalda ekan, kurs to‘liq bepul.» Ближе к «предложение», но суше.

### 10. «soatbay to‘lashsa / to‘lashar ekan»

- **Где:** P2 long, P3 mid и P3 long — «платят за часы».
- **Почему сомневаюсь:** «soatbay» («почасовой») — словарное слово, но в корпусе 0. Мог бы звучать как термин из бухгалтерии.
- **Запасной вариант:** «Vaqtingiz uchun to‘lashar ekan, …» — ближе к главной мысли «продаёшь время».

### 11. «AI orqali pul ishlashni qanday o‘rganishni mini-kursda ko‘rsatamiz»

- **Где:** P2 short — «Показываем на мини-курсе, как научиться зарабатывать на ИИ».
- **Почему сомневаюсь:** два винительных подряд («ishlashni … o‘rganishni») — грамматически верно, но тяжело для короткого текста.
- **Запасной вариант:** «Mini-kursda AI orqali pul ishlashni o‘rgatamiz» — как M7 «AI orqali $1000+ ishlashni o‘rgatamiz!». Минус: «учим» чуть сильнее, чем «показываем, как научиться».

### 12. «Bu — o‘z pulingizga ega bo‘lish yo‘li»

- **Где:** P3 long — «Это путь к своим деньгам».
- **Почему сомневаюсь:** дословно и правильно, но книжно.
- **Запасной вариант:** «Bu — o‘z pulingizga yashash yo‘li» — как в креативе I2-2: «o‘z pulimga yashamoqchiman». Ближе к боли пула («жить на свои»), но смысл чуть сдвигается: «жить на свои» вместо «иметь свои».

### 13. P1 short: «Yuqoridagi havola orqali…»

- **Полная фраза:** «Yuqoridagi havola orqali bepul ro‘yxatdan o‘tishga ulguring 👆»
- **Почему сомневаюсь:** перевод точный («по ссылке выше»). Но в Instagram над подписью стоит кнопка, а не ссылка, и «havola» может сбить с толку. Это вопрос к русскому оригиналу, не к языку.
- **Запасной вариант:** «Yuqoridagi tugma orqali bepul ro‘yxatdan o‘tishga ulguring 👆»

---

## Что не сомнение — взято из готовых креативов, чтобы подписи совпадали с картинками

- Название курса: «AI bilan 0 dan ilk $1000 gacha» (I1-2).
- «до конца дня» — «kun oxirigacha»; «0 сум вместо 3 млн» — «3 mln o‘rniga 0 so‘m — faqat kun oxirigacha» (M2).
- «вечер» — «kechqurun», «вечерами» — «kechqurunlari», «2–3 вечера в неделю» — «haftasiga 2–3 kechqurun». Не «kecha»: это «ночь» или «вчера» (финал корректора, 2-1b). Если носитель предпочтёт «oqshom», менять во всех файлах разом.
- «по $300», «по $100» — «$300 dan», «$100 dan»: цена за штуку, как «kilosi 20 mingdan» (финал корректора, V1).
- «Доход зависит от твоих действий» — «Daromad harakatlaringizga bog‘liq» (2-1).
- «план выхода на $1000» — «$1000 ga chiqish rejasi» (I3-1).
- «заказ» — «buyurtma», «клиент/заказчик» — «mijoz» (2-1, 2-3).
- Цитата в P3 — как в креативе I2-3, только без «umuman» («совсем»): в русском тексте пула этого слова нет. «Qanday qilib» здесь допустимо: это прямая речь подписчика (`ПРАВКИ-UZ-РЕДАКТОР.md`, I2-3).
- «Осталось 26 мест из 100» — «100 ta joydan 26 tasi qoldi», по модели «10 ta kanaldan 3 tasi» из карусели 2-3.
- «параллельно учёбе» — «o‘qish bilan birga», как у [Dona](https://www.facebook.com/ads/library/?id=2575636662885721) и [SMM AI Savodxon](https://www.facebook.com/ads/library/?id=2161315614777262). «из дома» — «uydan turib», как у [Smarthub](https://www.facebook.com/ads/library/?id=1047475578160800).
- «Хочешь дополнительный доход…?» — «…qo‘shimcha daromad qilishni xohlaysizmi?», как у [Qadam.online](https://www.facebook.com/ads/library/?id=3151275158402902).

---

## Как проверено (скрипт, сверка с `pools_ru.json`)

- **Структура:** во всех 18 текстах совпадают число абзацев и переносы строк внутри блоков (✅, 1️⃣…5️⃣).
- **Эмодзи:** в каждом абзаце те же и в том же порядке, в начале или в конце строки — как в русском.
- **Числа:**
  - все совпадают поштучно: $1000, $300, $100, 3–4, 2–3, 5, 3, 26, 100, 74, 0, 3 mln, 2,5–5 mln, 10;
  - новых цифр нет: «с первым уроком» — «birinchi dars», а не «1-dars».
- **Орфография:**
  - 140 знаков ‘ (U+2018), все после o или g;
  - тутук ’ не понадобился, 0;
  - 0 ASCII-апострофов, 0 знаков ` ʻ ʼ, 0 кириллических букв, 0 двойных пробелов, «ёлочки» парные.
- **Обращение:** везде «siz», призывы на -ing (bosing, oling, ro‘yxatdan o‘ting, boshlang).
- **Длина:** узбекский длиннее русского на 6–22%, порог 30% нигде не превышен.
- **Новых обещаний нет:** «kafolat», «tez boyish», «passiv daromad», «oson pul» — 0.
- `title_uz` добавлен в каждый пул, поле `unassigned` в файл не включено.
