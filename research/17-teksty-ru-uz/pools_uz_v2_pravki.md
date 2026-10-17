# Тексты под постами UZ — правки редактора, v1 → v2

**Итог.** Сделано 44 замены в 16 текстах из 18, плюс `title_uz` пула 2. По смыслу это 12 решений. Без изменений остались P1 short и P4 short.
Главное:
- смысловой сдвиг в хуке P1 mid: «qanday chiqasiz» → «qanday chiqiladi»;
- «neyrotarmoq» → «AI» в 18 местах из 19, теперь подпись совпадает с роликом V1 («Bu rolikni AI yaratdi»);
- «tuman» → «yaqin atrofingizdagi»;
- убраны «to‘lashar ekan», «bas qiling» и «bepul ochiq».

Числа, абзацы, строки и эмодзи не тронуты. `check_uz.py pools_uz_v2.json`: 0 ошибок, 0 предупреждений.
Вычитку делал ИИ (Claude) в роли носителя, как и перевод. Перед запуском нужен живой носитель, список вопросов к нему — в конце файла.

Корпус для всех чисел ниже — `../03-reklama-meta/ads_uz_info.csv`, строки `is_uzbek=True`: 832 объявления, 532 уникальных текста. «Текстов» — это уникальные тексты `body`. Апострофы (' ` ʻ ’ ‘) перед поиском сведены к одному знаку, регистр не учитывался.

---

## 1. Кнопка «Batafsil» — оставлена, но я бы поставил запасной вариант

В v2 «Batafsil» стоит везде одинаково, 17 раз, как требует ТЗ.

**Запасная формулировка — без названия кнопки:**

| Где | Сейчас (v2) | Запасной вариант |
|---|---|---|
| short, P2–P6 (👆 в конце) | «Batafsil» tugmasini bosib, ro‘yxatdan o‘ting 👆 | Ro‘yxatdan o‘tish uchun yuqoridagi tugmani bosing 👆 |
| mid и long, P2–P6 | 👆 «Batafsil» tugmasini bosib, ro‘yxatdan o‘ting. | 👆 Ro‘yxatdan o‘tish uchun yuqoridagi tugmani bosing. |
| P1 mid | 👆 «Batafsil» tugmasini bosing va boshlang. | 👆 Yuqoridagi tugmani bosing va boshlang. |
| P1 long | 👆 «Batafsil» tugmasini bosing va bepul kursni oling. | 👆 Yuqoridagi tugmani bosing va bepul kursni oling. |

**Я бы выбрал запасной вариант.** Почему:
- «Batafsil» как название кнопки в корпусе не встречается ни разу. Слово есть в 80 текстах: в 72 из них это оборот «batafsil ma’lumot», в остальных — наречие «подробно» («batafsil bilish uchun»).
- Кто называет кнопку, пишет по-русски: «Подробнее» — 19 текстов у 13 рекламодателей. Например, [Ozoda Fashion Academy](https://www.facebook.com/ads/library/?id=1600580618382943): «quyidagi «Подробнее» tugmasini bosib», [Iteach](https://www.facebook.com/ads/library/?id=1129400022747763): «“Подробнее” yoki “Learn more” tugmasini bosing». Значит, конкуренты сами не уверены, что зритель видит узбекскую подпись.
- Без названия кнопку зовут так же часто: «tugmani bosing» — 18 текстов. Например, [Edupro.uz](https://www.facebook.com/ads/library/?id=1052426477455494): «👆 Darsni olish uchun yuqoridagi tugmani bosing», [Registan LC](https://www.facebook.com/ads/library/?id=1048472567804871): «pastdagi tugmani bosing!».
- Узнать подпись в узбекском интерфейсе по корпусу нельзя. В колонке `cta` подписи английские («Learn more» — 242 объявления, «Sign up» — 146): библиотеку собирали в английском интерфейсе.
- Запасной вариант не врёт ни при каком языке интерфейса. Не врёт он и если в кабинете сменят тип кнопки, например на «Зарегистрироваться». Смысл русского «Жми «Подробнее»» сохраняется: «нажмите кнопку».

**Два условия перед заменой:**
- «yuqoridagi» («выше») верно для ленты Instagram: там кнопка стоит между картинкой и подписью. В ленте Facebook текст стоит над картинкой, а кнопка под ней. У 👆 в русском оригинале та же проблема, это решение по оригиналу, а не по языку. Если реклама идёт и в Facebook, «yuqoridagi» лучше убрать: «👆 Ro‘yxatdan o‘tish uchun tugmani bosing.»
- `check_uz.py` сверяет число «Подробнее» с числом «Batafsil». С запасным вариантом он выдаст 17 ошибок. Скрипт я не правил: проверку должен поменять тот, кто за неё отвечает.

---

## 2. Решения по терминам

### «neyrotarmoq» → «AI» (18 мест); «neyrotarmoqlar» во множественном числе оставлено в 1 месте

| Вариант | Текстов в корпусе | Упоминаний | Рекламодателей |
|---|---|---|---|
| AI | 46 | 71 | 23 |
| sun’iy intellekt | 45 | 61 | 25 |
| neyrotarmoq | 4 | 4 | 3 |
| neyroset | 0 | 0 | 0 |

- **Почему AI:**
  - AI встречается в корпусе так же часто, как «sun’iy intellekt», а короче в 8 раз.
  - На всех картинках стоит AI (глоссарий `creatives_uz.json`), в названии курса тоже: «AI bilan 0 dan ilk $1000 gacha».
  - Ролик пула 2 открывается сценой «Bu rolikni AI yaratdi» (V1). Теперь подпись повторяет её слово в слово: «Bu rolikni AI ikki soatcha vaqtda yaratdi».
- **Как конкуренты пишут «neyrotarmoq»:** все 4 раза во множественном числе и про инструменты. Примеры:
  - [Sfera academy](https://www.facebook.com/ads/library/?id=1092976069799567): «ChatGPT, Claude va Gemini kabi neyrotarmoqlardan»;
  - [Smmikramovna](https://www.facebook.com/ads/library/?id=1733681401255548): «Neyrotarmoqlar yordamida»;
  - [furkatovna.smm](https://www.facebook.com/ads/library/?id=1057114310531276): «neyrotarmoqlar orqali».
- **Правило для v2:**
  - «нейросеть» в единственном числе, «на нейросетях», «с нейросетью» → AI;
  - «нейросети» во множественном числе как инструменты → «neyrotarmoqlar».

  Такое место одно — P6 long: «✅ Boshlash uchun neyrotarmoqlar bepul». Пул 6 идёт с каруселями 2-1 («neyrotarmoqlar bepul») и 2-1b («bepul neyrotarmoqlar»), подпись совпадает с ними.
- **Смысл «нейросеть делает основную работу» сохранён:** «Asosiy ishni AI qiladi». Подлежащее, глагол и дополнение те же. В русских текстах «на AI» и «на нейросетях» и так синонимы.
- **Риск:** у конкурентов AI стоит только при послелогах bilan, yordamida, orqali (14 текстов) и ни разу не стоит подлежащим. Прецедент — только наш V1. Это вопрос живому носителю.

Места замены:
- P1 long — 1;
- P2 short — 1, mid — 2, long — 3;
- P3 long — 2;
- P4 mid — 1, long — 2;
- P5 short — 1, mid — 1, long — 1;
- P6 short — 1, mid — 1, long — 1.

### «tumaningizdagi» → «yaqin atrofingizdagi» (6 длинных текстов)

- **«tuman» в корпусе** — 16 текстов, и все они про адрес или административный район. Примеры:
  - [Centro Studio](https://www.facebook.com/ads/library/?id=996930146480158): «Mirobod tumani, Oybek 8»;
  - [Cambridge Innovation School](https://www.facebook.com/ads/library/?id=1670316590691866): «Farg‘ona viloyati, Rishton tumani»;
  - [Englify School](https://www.facebook.com/ads/library/?id=1091767420178834): «Parkent yoki Yangibozor tumanida yashasangiz».

  В Ташкенте это терпимо. В области tuman — это райцентр и десятки сёл. Русское «в своём районе» здесь значит «рядом с вами».
- **Чем плохи другие варианты:**
  - «mahalla» — 1 текст, и тот в адресе ([Varsovia](https://www.facebook.com/ads/library/?id=3190417114502734)). Для 3 компаний это слишком мелко, к тому же слово тянет за собой махаллинский комитет (MFY).
  - «hudud» — 4 текста, все официальные. Пример — [Genus Development](https://www.facebook.com/ads/library/?id=1417092440240944): «loyihasi hududida».
  - «yaqiningizdagi» — спотыкается о «yaqinlaringiz» («ваши близкие», 3 текста, например [gigu_school](https://www.facebook.com/ads/library/?id=1622683956175557): «O‘zingiz va yaqinlaringiz uchun»).
- **Что выбрано:** «yaqin atrof» — устойчивое «округа, поблизости». Одинаково работает для Ташкента и областей. В корпусе 0, то есть решение по норме языка, а не по корпусу. Длиннее на 6 знаков.

### Единообразие — проверено по v2

| Термин | Раз в v2 | Комментарий |
|---|---|---|
| mini-kurs | 18 | во всех 18 текстах, в P2 short — с заглавной в начале фразы («Mini-kursda»). Других написаний (minikurs, mini kurs) — 0 |
| AI-mutaxassis | 4 | P2 mid и long, P6 mid и long. «AI mutaxassis» — 0 |
| ilk $1000 | 10 | 6 в названии курса и 4 в «AI bilan ilk $1000 ga qanday chiqish» |
| kun oxirigacha | 17 | во всех текстах, кроме P1 mid: там по оригиналу срока нет («Пока действует предложение»). В 4 местах с заглавной: «⏳ Kun oxirigacha kurs bepul» |
| 100 ta joydan 26 tasi qoldi | 15 | P2–P6 × 3. В P1 long своя фраза по русскому оригиналу: «Jami 100 ta joy, 74 tasi allaqachon band» |
| «Batafsil» | 17 | одна форма кавычек |
| kechqurun / kechqurunlari | — | «вечером» → kechqurun, «вечерами / по вечерам» → kechqurunlari, как на картинках после финала корректора |

---

## 3. Правки: пул · длина · было → стало · почему

1. **P1 · mid · хук.** «…oyiga $1000 ga qanday chiqasiz?» → «…oyiga $1000 ga qanday **chiqiladi**?»
   - «chiqasiz» значит «как вы выйдете», то есть вопрос о планах читателя. Русское «как выйти» — обещание инструкции.
   - Безличная форма взята из глоссария (`creatives_uz.json`: «в вопросе — «… $1000 ga qanday chiqiladi?»»). Так же написан креатив I1-2 этого пула: «Masofadan pul ishlashni boshlab, $1000 ga qanday chiqiladi?».
   - Условие на «siz» плюс безличный вопрос — обычная узбекская конструкция.

2. **P1 · mid и long.** «Vaqtingizni sotishni **bas qiling** — natijani soting.» → «Vaqtingizni sotishni **to‘xtating** — natijani soting.»
   - «bas qiling» значит «хватит!»: так одёргивают. В корпусе 0.
   - «…ni to‘xtating» — нейтральное «перестаньте», оттенок «перестань» из русского сохранён. Корпус: to‘xtat* — 6 текстов, например [You tube konsul](https://www.facebook.com/ads/library/?id=792670210325876): «Sizni nima to‘xtatyapti?».
   - Тот же глагол уже стоит в P3 mid: «vaqtni sotishni to‘xtatib».
   - Запасной вариант переводчика «Vaqtingizni emas, natijani soting» не взял: пропадает «перестань».

3. **Все пулы · 18 мест.** neyrotarmoq → AI. Обоснование — в разделе 2.

4. **P1–P6 · long.** «tumaningizdagi 3 ta kompaniya» → «yaqin atrofingizdagi 3 ta kompaniya». Обоснование — в разделе 2.

5. **P2 и P3 · short, mid, long.** «kurs (kun oxirigacha) bepul **ochiq**» → «kurs (kun oxirigacha) bepul»
   - «bepul ochiq» в корпусе — 11 текстов, и во всех 11 дальше идёт «dars»: «bepul ochiq dars», то есть «открытый урок». Примеры — [Proweb](https://www.facebook.com/ads/library/?id=1005774469144993): «bepul ochiq darsda», [interno.school.uz](https://www.facebook.com/ads/library/?id=2907418496275290): «Bepul ochiq darsdan boshlang».
   - «Kurs bepul ochiq» читается как сдвинутый термин. «Kun oxirigacha kurs bepul» — тот же смысл, срочность на месте.

6. **P2 · short.** «AI orqali pul ishlashni qanday o‘rganishni mini-kursda ko‘rsatamiz» → «Mini-kursda AI orqali pul ishlashni o‘rgatamiz»
   - Два винительных подряд («…ishlashni … o‘rganishni») тяжелы для короткого текста.
   - Модель — креатив M7: «AI orqali $1000+ ishlashni o‘rgatamiz!». В корпусе «o‘rgatamiz/o‘rgataman» — 19 текстов, например [Barno Askarova](https://www.facebook.com/ads/library/?id=1771826157380200).
   - Сдвиг: «показываем, как научиться» стало «учим». Нового обещания нет: курс и есть обучение. Если нужно дословно — «AI orqali pul qanday ishlanishini mini-kursda ko‘rsatamiz», по модели M4.

7. **P2 long и P3 long.** «Sizga soatbay to‘lashar ekan, …» → «Ishlagan soatingiz uchun to‘lashsa, …»
   **P3 mid.** «Soatbay to‘lashsa, …» → «Ishlagan soat uchun to‘lashsa, …»
   - «…to‘lashar ekan» в начале фразы читается как пересказ: «оказывается, вам платят почасово». Нужно было «пока платят».
   - «soatbay» — слово из ведомостей и вакансий («soatbay ish haqi»), в корпусе 0.
   - «Ishlagan soat uchun» — разговорно и по модели карусели 2-1b: «rulda o‘tirgan soatga to‘lashadi».
   - В P3 mid получилась параллель со следующей фразой: «Tayyor sayt, bot yoki dizayn uchun to‘lashsa — cheklanmaydi».

8. **P3 · mid.** «hatto hozir bularning hech birini **qila olmasangiz** ham» → «… hech birini **qilishni bilmasangiz** ham»
   - Русское «не умеешь» — это «bilmaslik», а «qila olmaslik» — «не можешь». То же различие провёл прошлый редактор в I3-3: «topishni bilmaysizmi».
   - В корпусе есть модель — [Logist Academy](https://www.facebook.com/ads/library/?id=2225728551508423): «Til bilmasangiz ham — ish sizniki!».

9. **P3 · long.** «Bu — o‘z pulingizga **ega bo‘lish** yo‘li» → «Bu — o‘z pulingizni **topish** yo‘li»
   - «…ga ega bo‘lish» — письменный регистр. В корпусе 4 текста, все в канцелярских оборотах, например [Smarthub](https://www.facebook.com/ads/library/?id=1609298507478618): «online ishlash imkoniyatiga ega bo‘lishingiz mumkin».
   - «pul topish» значит «зарабатывать» (глоссарий). У того же [Smarthub](https://www.facebook.com/ads/library/?id=1609298507478618): «Pul topish uchun…». «O‘z pulini topadi» — так говорят о самостоятельных.
   - Смысл «путь к своим деньгам» сохранён. Запасной вариант переводчика «o‘z pulingizga yashash» не взял: смысл сдвигается в «жить на свои».

10. **P4 · mid и long.** «Biznes sayt, Telegram-bot, dizayn va Reels uchun pul to‘laydi.» → «Sayt, Telegram-bot, dizayn va Reels uchun biznes pul to‘laydi.»
    - «Biznes sayt» в начале фразы читается как одно слово «бизнес-сайт», и фраза остаётся без подлежащего до конца перечня.
    - Перечень вынесен вперёд, «biznes» стоит перед глаголом: двусмысленности нет, слова те же.

11. **P5 · mid и long.** «biznes **ijrochi** qidiradigan top-10 kanal» → «biznes **mutaxassis** qidiradigan top-10 kanal»
    - «ijrochi» в быту значит «исполнитель песен», в корпусе 0. «mutaxassis» — 58 текстов.
    - Карусель 2-3 — креатив этого же пула. По ней в этих каналах ищут «dizayner, SMMchi va mobilograf», то есть специалистов.

12. **P5 · long.** «aynan **siz** qaysi biridan **boshlashingizni** maslahat beramiz» → «aynan **sizga** qaysi biridan **boshlashni** maslahat beramiz»
    - Глагол «maslahat bermoq» требует «кому» (sizga) и инфинитив. Так же уже написано в P1 long: «sizga qaysi biridan boshlashni maslahat beramiz».

Служебное поле: **P2 · title_uz.** «Rolikni neyrotarmoq yaratdi (…)» → «Rolikni AI yaratdi (…)». В рекламу оно не идёт, поправил ради единого термина.

---

## 4. Сомнения переводчика, которые я не трогал

- **«Vaqtingizni arzimagan pulga sotyapsizmi?»** (P2, все три длины). Оставил.
  - «arzimagan pul» — обиходное «гроши».
  - В корпусе 0 у всех вариантов: arzimagan, arzimas, tiyin, chaqa. Корпус спор не решает.
  - «arzon» (5 текстов, «arzonga» в креативе I3-3) значит «дёшево», с ним хук слабее.
  - Вопрос живому носителю: сравнить с идиомой «arzon-garovga» («за бесценок»).
- **«Talaba bo‘lsangiz»** (P1 mid). Оставил.
  - «talaba» — 24 текста, например [Galaktika](https://www.facebook.com/ads/library/?id=4560467967509995).
  - «o‘qiyotgan» — 0 и двусмысленно: ещё и «читающий».
  - Минус: «talaba» — только вуз и колледж, а русское «учишься» шире.
- **«Aksiya davom etar ekan, kurs to‘liq bepul»** (P1 mid). Оставил.
  - Оборот «…ekan» в значении «пока» прошлый редактор принял в M7.
  - «aksiya» в значении «промо» есть у [Asakabank](https://www.facebook.com/ads/library/?id=1103927438742247): «Aksiya … davom etadi».
  - Чем отличается от правки 7: здесь оба прочтения («пока идёт акция» и «акция, говорят, идёт») ведут к одному смыслу.
- **«Yuqoridagi havola orqali»** (P1 short). Оставил.
  - «havola orqali» — 50 текстов, так конкуренты называют и кнопку.
  - Что над подписью — ссылка или кнопка, — вопрос к русскому оригиналу.
- **«bunaqasini esa bizneslarga $100 dan sotishadi»** (P2). Оставил: множественное «bizneslarga» есть в корпусе (5 текстов). Пример — [SMM AI Savodxon](https://www.facebook.com/ads/library/?id=2161315614777262): «bizneslarga xizmat taklif qilib».
- **«Uyda noutbuk va haftasiga 2–3 kechqurun yetarli»** (P6 mid). Оставил: «из дома» передано через «uyda», смысл тот же.

---

## 5. Что проверить живому носителю (по убыванию риска)

1. Кнопка: «Batafsil» или запасной вариант из раздела 1. Заодно посмотреть, как подписана кнопка «Подробнее» в узбекском интерфейсе Facebook и Instagram. Это не проверено.
2. AI как подлежащее: «Asosiy ishni AI qiladi», «AI bajaradi», «Bu rolikni AI … yaratdi». В корпусе AI только при послелогах, подлежащим не стоит ни разу.
3. «yaqin atrofingizdagi 3 ta kompaniya»: в корпусе 0, решение по норме языка.
4. «arzimagan pulga» или «arzon-garovga» в хуке P2.
5. «Ishlagan soat(ingiz) uchun to‘lashsa» (P2 long, P3 mid, P3 long): звучит ли естественно.
6. Порядок слов «Sayt, Telegram-bot, dizayn va Reels uchun biznes pul to‘laydi» (P4).
7. «Talaba bo‘lsangiz»: если в таргет входят школьники и колледж, нужна более широкая формулировка.

---

## 6. Как проверено

- `python3 check_uz.py pools_uz_v2.json` (из папки `17-teksty-ru-uz`): **ошибок 0, предупреждений 0**. Рост длины в среднем 1,12, максимум 1,20. У v1 было 1,14 и 1,22.
- Структура та же, что у v1: 6 пулов, поля `n`, `title`, `title_uz`, `status`, `creatives`, `pain`, `texts`. Изменились только 16 текстов и `title_uz` пула 2.
- Орфография:
  - 140 знаков ‘ (U+2018), все после o или g;
  - тутук ’ — 0;
  - ASCII ' и `, ʻ и кириллица — 0;
  - двойных пробелов — 0.
- Новых слов-обещаний нет: «kafolat», «tez», «oson pul», «passiv daromad» — 0.
- Числа, суммы, эмодзи и их порядок, число абзацев и строк совпадают с русским — это проверяет скрипт.
