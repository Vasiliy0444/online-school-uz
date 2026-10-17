# Тексты под постами UZ, пулы 7–9, v1 — что проверить живому носителю

Файл перевода: `pools_uz_p79_v1.json` (3 пула × 3 длины = 9 текстов). Перевод сделал ИИ (Claude) в роли копирайтера из Ташкента. Перед запуском нужна вычитка живым носителем.

Корпус — `../03-reklama-meta/ads_uz_info.csv`, строки `is_uzbek=True` (532 уникальных текста). «0 в корпусе» значит, что конкуренты так не пишут. Это ещё не значит, что так писать нельзя.

**Что взято из готовых пулов 1–6 дословно** (сверено строкой с `pools_uz_final.json`): оба призыва с ⏳ и 👆, «3 mln o‘rniga 0 so‘m — faqat kun oxirigacha…», буллеты про 5 услуг, план на $1000 и топ-10 каналов, «yaqin atrofingizdagi 3 ta kompaniyani topib, ularga sayt yasaysiz», «Toshkentdagi studiyalar oddiy sayt uchun 2,5–5 mln so‘m so‘raydi», «Telegramdagi bepul mini-kursda — darslar va amaliyot:», название курса, «kod yozish shart emas». По ним вопросов нет. Две старые темы из `pools_uz_v2_pravki.md` касаются и этих пулов: кнопка «Batafsil» (8 раз) и AI в роли подлежащего (P9: «AI bajardi»).

**Как проверено.** `check_uz.py` не запускал. Те же проверки прогнал отдельным скриптом на 3 пула: кириллица, апострофы, «sen», абзацы, строки, эмодзи, числа, «Batafsil». Ошибок 0. Знаков ‘ — 70, все после o/g. Тутук ’ — 3, это «va’dasimi» в P9. Рост длины в среднем 1,13, максимум 1,21 (P9 short). У пулов 1–6 максимум был 1,20.

---

## Сомнения: от самого рискованного

### 1. P8 · short, mid, long · «Ko‘p odam chetga ishlagani ketadi»
- **Почему сомневаюсь:** тема чувствительная. Фраза взята дословно из карусели 2-4 этого пула (финал после трёх проверок), чтобы подпись и картинка совпадали. В корпусе «chetga» и «ishlagani» — 0. «chet el» — 4 текста, все про учёбу за границей. Корпус спор не решает.
- **Запасной вариант:** «Ko‘p odam chet elga ishlagani ketadi» — однозначнее, плюс 3 знака. «…musofirchilikka ketadi» — теплее, но тянет тоску и тяготы: эмоция сильнее, чем в русском. Не брал «mardikor» (оттенок чернорабочего) и «migrant» (язык новостей). Если меняете, то вместе с каруселью 2-4.

### 2. P8 · mid, long · «Bilak kuchi bilan emas, aql bilan ishlaysiz»
- **Почему сомневаюсь:** это идиома «головой, а не спиной». В корпусе 0 у всех вариантов: bilak, aql bilan, kuch bilan, aqliy. Риск тот же, что в русском: для тех, у кого родные работают за границей, фраза может прозвучать свысока. Носителю стоит проверить именно тон.
- **Запасной вариант:** A — «Jismoniy emas, aqliy mehnat qilasiz»: нейтрально, но книжно. B — «Bilak bilan emas, bilim bilan ishlaysiz»: отсылает к пословице «Bilagi zo‘r birni yiqar, bilimi zo‘r mingni yiqar». Звучит живее, но «bilim» — это «знания», а не «голова».

### 3. P8 · short, mid, long · «Uyda» в значении «дома, на родине»
- **Фраза:** «Uyda, oila yonida pul ishlashning iloji bormi?», «Uyda ham mijozlar bor».
- **Почему сомневаюсь:** на карусели 2-4 «Uyda» стоит меткой, и в паре с «U yerda» понятно, что речь о родине. В подписи «Uyda ham mijozlar bor» можно прочитать буквально: «в доме тоже есть клиенты».
- **Запасной вариант:** «O‘zimizda ham mijozlar bor» — разговорное «у нас тут тоже». Или «Shu yerda ham mijozlar bor».

### 4. P9 · short, mid, long · хук «Yana «AI orqali $1000» va’dasimi?»
- **Почему сомневаюсь:** чтобы вопрос был грамматичным, добавил слово «va’da» («обещание»). В русском его нет, оно подразумевается. В корпусе так скептики и пишут: [Hirex](https://www.facebook.com/ads/library/?id=1258670336344494) — «Quruq va’dalar emas», [Kosmedia.uz](https://www.facebook.com/ads/library/?id=27873549662341793) — «havoyi va’dalar bermaydi». Риск: слово подчёркивает, что $1000 — это обещание, а наш курс тоже про $1000.
- **Запасной вариант:** «Yana o‘sha «AI orqali $1000»mi?» — ближе всего к русскому, но частица -mi после кавычки на письме выглядит странно. «Yana «AI orqali $1000» degan gapmi?» — разговорно, но «gap» повторится в следующей фразе («Quruq gapga…»).

### 5. P9 · short, mid, long · «Quruq gapga ishonmang»
- **Почему сомневаюсь:** это «Не верь на слово». «quruq gap» — «пустые слова», в корпусе «quruq» в этом смысле есть только как «Quruq va’dalar» (Hirex). Для скептика сочетание естественное, но живой носитель может предложить разговорнее.
- **Запасной вариант:** «So‘zga ishonmang» — дословнее, но суше. «Gapimga ishonmang» не брал: смысл сдвигается в «не верь мне».

### 6. P9 · mid, long · «Kod yozmadim: men topshiriq berdim, AI bajardi, men tekshirdim.»
- **Почему сомневаюсь:**
  - «Без программирования» передал как «kod yozmadim» («кода не писал»). На картинке I3-2 стоит другое: «dasturlashni bilmasdan» («не зная программирования»). Держался русской подписи, а не картинки.
  - Простое прошедшее («berdim, bajardi, tekshirdim») звучит чётко и повторяет схему P2 («siz topshiriq berasiz, AI bajaradi, siz tekshirasiz»). Русские глаголы несовершенного вида («ставил, делала, проверял») передают процесс.
- **Запасной вариант:** «Dasturlash shart bo‘lmadi: …». Процесс можно передать формой на -ardi: «men topshiriq berardim, AI bajarardi, men tekshirardim».

### 7. P7 · short, mid, long · хук «Xizmatingizni arzonga sotasizmi?»
- **Почему сомневаюсь:** в русской подписи «берёшь дёшево за свою работу», а на картинке I3-3 — «за свои услуги». Взял формулировку с картинки (она в финале), чтобы подпись повторяла заголовок креатива. Вопросы идут отдельно, без «va», как редактор правил в I3-3.
- **Запасной вариант:** «Ishingiz uchun kam pul olasizmi?» — ближе к русскому. «Arzonga ishlaysizmi?» — короче всех и разговорно.

### 8. P8 · mid, long · «U yerda boshida daromad ko‘proq, lekin patent, ijara va ovqat uning bir qismini yeb ketadi»
- **Почему сомневаюсь:**
  - На карусели слова «деньги» нет («U yerda boshida ko‘proq»). В подписи я добавил «daromad»: без него не на что сослаться словом «uning», а в русском «заработка» стоит в той же фразе.
  - «Жильё» стало «ijara» («аренда»), как на карусели.
  - «yeb ketadi» («съедают») — обиходная метафора про расходы. В корпусе 0, «patent» тоже 0.
- **Запасной вариант:** «U yerda boshida ko‘proq topiladi, lekin topganingizning bir qismi patent, ijara va ovqatga ketadi».

### 9. P8 · short, mid, long · «…pul ishlashning iloji bormi?»
- **Почему сомневаюсь:** русское «А можно…?» звучит с надеждой, без оценки. «…ning iloji bormi?» — «есть ли возможность», это норма. «Oila yonida» написал без «-ingiz», в отличие от карусели («oila yoningizda»): хук не должен утверждать, что у читателя есть семья (правило Meta о личных признаках, ради него на карусели оставлено третье лицо).
- **Запасной вариант:** «Uyda, oila yonida pul ishlasa bo‘ladimi?».

### 10. P7 · mid, long · «munosib narx so‘raydiganlar»
- **Почему сомневаюсь:** это «называет нормальную цену». В корпусе 0 и у «munosib narx», и у «normal narx». «munosib» («достойный») чуть книжное, «normal» разговорное, но это русизм.
- **Запасной вариант:** «normal narx so‘raydiganlar».

### 11. P7 · short, mid, long · «Qila oladiganlar ko‘p, pulni esa mijoz topadiganlar ishlaydi»
- **Почему сомневаюсь:** русское «платят тем, кто находит заказчиков» перевёл как «деньги зарабатывают те, кто находит клиентов». Оборот с вынесенным вперёд дополнением «pulni esa … ishlaydi» разговорный, носитель должен подтвердить, что он не режет слух. В mid и long то же самое: «Sayt (yoki) va bot yasay oladiganlar ko‘p. Pulni esa…».
- **Запасной вариант:** «…pul esa mijoz topa oladiganlarga to‘lanadi». Ближе к «платят тем», но страдательный залог звучит книжно.

### 12. P7 · mid, long · «birjasiz»
- **Почему сомневаюсь:** «birja» в корпусе 0, «frilans» — 2 текста. Карусель 2-3 этого же смысла уже пишет «Birjasiz mijoz qayerdan topiladi». Риск: «birja» в Узбекистане — прежде всего фондовая или товарная биржа.
- **Запасной вариант:** «frilans saytlarisiz».

### 13. P7 · long · «daromad esa beqaror: goh deyarli hech narsa, goh yaxshi»
- **Почему сомневаюсь:** «скачет» передал как «beqaror» («нестабильный»), образ потерялся. В корпусе «barqaror» — 7 текстов (глоссарий), «beqaror» — 0.
- **Запасной вариант:** «daromad esa sakrab turadi: …». Образ сохраняется, но может звучать как калька.

### 14. P7 · long · «— narxingiz uchun mo‘ljal shu»
- **Почему сомневаюсь:** по словарю «ориентир» — это «mo‘ljal». Но в корпусе (14 текстов) слово стоит только в «mo‘ljallangan» («предназначен») и в адресах («Mo‘ljal: … ro‘parasida»), то есть «ориентир на местности».
- **Запасной вариант:** «— narxni shunga qarab qo‘yasiz» («цену ставите, глядя на это»). Смысл тот же, формой совет.

### 15. P8 · mid, long · «uyingizga yaqin» вместо «yaqin atrofingizdagi»
- **Почему сомневаюсь:** русское «рядом с домом» в P8 и «в своём районе» в остальных пулах я развёл сознательно. В P8 главное слово — «дом». Модель в корпусе — [Sodiq School](https://www.facebook.com/ads/library/?id=2027023727947595): «Uyingizga yaqin joyda». Если редактор хочет одну формулу на все пулы, можно поставить «yaqin atrofingizdagi», но тогда пропадёт «дом».
- **Запасной вариант:** «yaqin atrofingizdagi 3 ta kompaniyani».

---

## Что проверить живому носителю, коротко

1. P8, пункты 1–3: «chetga ishlagani», тон «Bilak kuchi bilan emas, aql bilan», «Uyda ham mijozlar bor».
2. P9, хук: «Yana «AI orqali $1000» va’dasimi? Quruq gapga ishonmang».
3. P7, хук: формулировка с картинки I3-3 или ближе к русскому.
4. Остальное — пункты 6 и 8–15. Это выбор слова, смысл не меняется.
