# Правки UZ — проверка 1, редактор (11.10.2026)

Что проверено: `creatives_uz_v1.json` (fields_uz, alt_uz, video_extra_uz) и `creatives_uz_type2.json` (карусели 2-1, 2-1b, 2-3, 2-4). Сверка шла с `creatives_ru.json`, с `04-texts-static.json` и с корпусом из 220 объявлений конкурентов.
Что получилось: `creatives_uz_v2.json` и `creatives_uz_type2_v2.json`. Файлы v1 не тронуты.

Вычитку сделал ИИ (Claude) в роли редактора-носителя. Перед запуском всё равно нужен живой носитель, в первую очередь для M1 и 2-4.

**Итог:** 11 правок в 11 креативах, это 16 полей. Цифры и цены не менялись. 0 ASCII-апострофов, 0 обращений на «sen».

---

## Нельзя пускать в рекламу как есть

1. **M1 в версии v1 (`O‘rgan` + плашка `Ing`).** Белое слово «O‘rgan» стоит в рамке пародии на логотип порносайта и читается как «ORGAN». Пошлую шутку увидят и узбекоязычные, и русскоязычные зрители, засмеют в комментариях. В v2 слово заменено на «Yarat|Ing». **Сам формат пародии на Pornhub остаётся риском для УЗ**, текст его не снимает: закон о рекламе (общественная мораль), модерация Meta (намёк на контент для взрослых), негатив семей. Совет — та же композиция, но плашка без узнаваемой отсылки. Решает Вася.
2. **I1-3: в заголовке стоит заглушка «X so‘m».** Без реальной суммы и настоящих скринов не запускать. Это уже отмечено в `ПРОВЕРКА-КРЕО.md`.
3. **2-4 (волна 2).** Текст после правки в порядке. Но тема отъезда на заработки чувствительна, и в `check` стратегии прямо сказано: «Перевод — носитель языка». Перед запуском нужен живой носитель и юрист или малый бюджет.

---

## Правки: id, поле: было → стало — почему

### creatives_uz_v2.json

1. **I1-1, headline:** «Qanday qilib 2026-yilda AI orqali oyiga barqaror $1000 daromadga chiqish mumkin?» → «2026-yilda AI orqali oyiga barqaror $1000 qanday topiladi?»
   - Почему: «Qanday qilib … mumkin» — та самая калька «как можно…». «$1000 daromadga chiqish» — канцелярит. Безличное «… qanday topiladi?» («pul topish» = зарабатывать) — живой вопрос. Оба действия оригинала («заработать на ИИ», «выйти на стабильные $1000 в месяц») уместились в один глагол. Было 80 знаков, стало 58 (русский — 69).

2. **I1-2, headline:** «Masofaviy ishni qanday boshlash va $1000 ga chiqish mumkin?» → «Masofadan pul ishlashni boshlab, $1000 ga qanday chiqiladi?»
   - Почему: «masofaviy ish» — язык вакансий и вузов («masofaviy ta’lim»), молодёжь говорит «masofadan ishlash». «qanday X va Y mumkin» — калька «как начать… и выйти…». Деньги вернулись в глагол («pul ishlash» = «зарабатывать», как в оригинале). 58 знаков.

3. **I1-2, alt_uz.headline:** «Masofadan pul ishlashni qanday boshlash va $1000 ga chiqish mumkin?» → «Masofadan ishlab, $1000 ga qanday chiqiladi?»
   - Почему: дословный запасной вариант был той же калькой. Теперь запас — короткий вариант без «начать», 44 знака.

4. **I3-1, headline:** «$1000 ga chiqish rejasini sovg‘a qilaman» → «Sovg‘a: $1000 ga chiqish rejasi»
   - Почему: строка была на 60% длиннее русской, и в макете «блоками» заголовок уходил в 3–4 строки. «Sovg‘a:» первым словом — тот же «Дарю…» и в том же порядке, по модели «chek-list sovg‘a» у [Interno Management School](https://www.facebook.com/ads/library/?id=27676140485373532). 31 знак.

5. **I3-1, alt_uz.headline:** «$1000 ga chiqish rejasi — sovg‘a» → «$1000 ga chiqish rejasini sovg‘a qilaman»
   - Почему: короткий вариант стал основным, а дословный с «я дарю» ушёл в запас.

6. **I3-3, headline:** «Mijoz topishni bilmaysizmi va xizmatingizni arzonga sotasizmi?» → «Mijoz topishni bilmaysizmi? Xizmatingizni arzonga sotasizmi?»
   - Почему: два вопроса с -mi, сшитые через «va», — русский синтаксис. По-узбекски боли ставят отдельными вопросами подряд, как у [Aziz Djamolov](https://www.facebook.com/ads/library/?id=27697016846614369): «Tur agentlik ochmoqchimisiz? … Arzon sayohat qilishni xohlaysizmi?». Слова те же.

7. **M1, logo_word_white:** «O‘rgan» → «Yarat» (плашка «Ing» без изменений)
   - Почему: «O‘rgan» в рамке порно-логотипа читается как «ORGAN». «Yarat|Ing» = «Yarating» («создавайте»): белая часть — обычное слово, в плашке те же 3 буквы, логотип ровный, как «Науч|Ись».
   - Чем жертвуем: «научись» уходит из логотипа, учёбу несёт кнопка «Bepul mini-kurs».
   - Запасной вариант, точный по смыслу: «O‘zlashtir|Ing» («освойте») с прежней line1. Минус — белое слово в 10 знаков, логотип перекошен. Деление «O‘rga|ning» не спасает: в той же рамке читается «ORGA…».

8. **M1, line1:** «AI yordamida sayt, bot va Reels yaratishni.» → «AI yordamida sayt, bot va Reels.»
   - Почему: глагол теперь в логотипе, иначе «yarating … yaratishni» повторяется.

9. **M2, blocks[5].text:** «Bosing! Nima kutyapsiz?» → «Bosing! Nimani kutyapsiz?»
   - Почему: у «kutmoq» вопросительное дополнение стоит в винительном. «Nimani kutyapsiz?» — привычная фраза, «Nima kutyapsiz?» звучит небрежно.
   - Строка и так переносилась в 2 строки, и на v1 тоже. Разметка ~~, [[ ]], == и параметры блоков не тронуты.

10. **M2, lines[4]:** «Bosing. Nima kutyapsiz?!» → «Bosing. Nimani kutyapsiz?!»
    - Почему: так же, как в п. 9. Поле не рендерится, но должно совпадать с blocks.

11. **M4, line1:** «AI orqali qanday pul ishlash mumkin?» → «AI orqali pul qanday ishlanadi?»
    - Почему: «qanday pul» подряд читается и как «какие деньги». Плюс это калька «qanday … mumkin». «Pul qanday ishlanadi?» — живой вопрос, 31 знак.
    - Связка с line2 «Kursda o‘rganing!» сохранена: «Как заработать на AI? — Научитесь на курсе!»

12. **M5, headline:** «AI orqali daromad kursini tarqatamiz!» → «AI orqali pul ishlash kursini tarqatamiz!»
    - Почему: «daromad kursi» значит «курс дохода», а «kurs» по-узбекски ещё и «курс валюты» («dollar kursi»), так что фраза спотыкается. Правильная модель — «[действие] + kursi», как «AI KONTENT YARATISH KURSI» у [Morgouza Ai](https://www.facebook.com/ads/library/?id=2156950881915390).
    - Длина: 41 знак, на 28% длиннее русского. Это 3 строки, FIT_JS ужмёт.

### creatives_uz_type2_v2.json

13. **2-1b, headline_uz и cards[1].title_uz:** «O‘qish bilan qaysi ish mos keladi?» → «O‘qish bilan qaysi ish mos?»
    - Почему: строка была на 42% длиннее «Что совместить с парами?», стала на 12%. «bilan» сохраняет смысл «совместить». Вопрос «…qaysi … mos?» — живой, как «Qaysi yo'l menga mos?» у [Shahlo.alikhanova](https://www.facebook.com/ads/library/?id=2266546904194108).
    - Первая карточка изменена так же: заголовок и карточка 1 должны совпадать дословно, иначе build.py вставит лишнюю карточку.

14. **2-3, cards[5].text_uz:** «U yerda dizayner, SMM va mobilograf qidirishadi. …» → «U yerda dizayner, SMMchi va mobilograf qidirishadi. …»
    - Почему: в перечне людей «SMM» — название сферы, а не человек. В чатах вакансий пишут «SMMchi kerak».

15. **2-4, headline_uz:** «Ko‘pchilik chetga ishlagani ketadi. Halol solishtirdik» → «Ko‘p odam chetga ishlagani ketadi. Halol solishtirdik»
    - Почему: «ko‘pchilik» в рекламе значит и «многие», и «большинство». Пример — «Ko‘pchilik … deb o‘ylaydi» у [Worldwide Consulting](https://www.facebook.com/ads/library/?id=1813142696309475).
    - Чтение «большинство уезжает» — это утверждение о статистике, которого в источниках нет (1,4 млн за границей, древо, гл. 6 — не большинство). «Ko‘p odam» = «многие», разговорно и однозначно. Третье лицо сохранено.

Всего 15 пунктов и 16 полей: пункт 13 — одна правка в двух полях. По смыслу это 11 правок, по одной на креатив. У I1-2 и I3-1 правка идёт вместе с запасным вариантом, у M1 — логотип и строка, у M2 — blocks и lines.

---

## Оставил без изменений — почему так хорошо

- **I1-1:** CTA «3 ta bepul darsni oling» — прямой призыв на «siz». «3 ta» стоит по норме, «barqaror» — как «barqaror daromad» у [MAAB Academy](https://www.facebook.com/ads/library/?id=1972455443721632).
- **I1-2:** «Bepul mini-kursda bilib oling» и название «AI bilan 0 dan ilk $1000 gacha». Модель «0 dan … gacha» — как «0 dan 100 gacha» у [Myfxbro](https://www.facebook.com/ads/library/?id=1095898190053365), «ilk» живее «birinchi».
- **I1-3:** «yasashga 2 kecha ketdi» — разговорное «ушло 2 вечера». «Siz ham xohlaysizmi?» и «Bepul kursga ro‘yxatdan o‘ting!» — формулы корпуса.
- **I1-4:** «pul ishlashning 5 usuli» — как «Internetda pul ishlashning qonuniy usuli» у [Uznetix](https://www.facebook.com/ads/library/?id=1687841545835931). «Telegramda» слитно.
- **I2-1:**
  - Вопрос короткий, как пишут в директ.
  - «darsni o‘rganib» — та же форма, что учительское «darsni o‘rganib keling» («изучи урок»).
  - Буллеты «sarmoyasiz / dasturlashni bilmasdan / mutlaqo noldan» короче русских.
- **I2-2:**
  - «pul olaverish jonimga tegdi» — живое «достало» в форме -averish. Ту же конструкцию даёт [Antisilverin](https://www.facebook.com/ads/library/?id=1294160482268902).
  - «Nima maslahat berasiz?» — к блогеру на «вы».
  - Если захочется мягче: «…olaverishdan charchadim».
- **I2-3:**
  - «Kun bo‘yi ishlayman… Qanday qilib ko‘proq pul topsam bo‘ladi?» — так пишет живой человек. Здесь «qanday qilib» уместно: это речь подписчика, а не заголовок.
  - «Mini-kurs tayyorladim: unda…» — как «BEPUL dars tayyorlab qo'ydim» у [Edupro.uz](https://www.facebook.com/ads/library/?id=1052426477455494).
- **I2-4:** лучший вопрос набора. «kerak-ku...» передаёт досаду, «KO‘P» капсом стоит в конце, как «МНОГО». «3 oydayoq» = «уже через 3 месяца», обещание не усилено.
- **I3-1:** подзаголовок «Masofaviy kasb: biznes uchun AI-mutaxassis», буллеты и CTA «Pastdagi havola orqali 0 so‘mga oling» — формулы корпуса.
- **I3-2:** порядок фактов как в оригинале. «1 kechada» = «за один вечер». «$200 ga sotdim» — суффикс через пробел, как «$1.000 gacha» у конкурентов.
- **I3-3:** подзаголовок «…2 oydayoq ilk $1000 ga chiqing» — частица -yoq значит «уже», обещание не усилено. «Bepul mini-kurs — havolada» коротко.
- **V1:**
  - «Bunaqasini mijozlarga $100 dan sotamiz», «ikki soatcha», «olishga ulguring, hozircha bepul» — разговорно и точно.
  - kw4/kw5 дословно есть в сценах 4 и 5, подсветка срабатывает (проверено вызовом video.py).
  - «Bepul ko‘rish» — как кнопка «BEPUL KO'RISH» у Shahlo.
- **V2:**
  - «Sayt zo‘r chiqibdi» и «bot yasashni bilar ekansiz» (-ekan вместо «говорят») — так пишут в мессенджерах.
  - Дата «Yakshanba, 11-oktabr» верна: 11.10.2026 — воскресенье.
- **M1:** «Bunga pul to‘lashadi.» и «Bepul mini-kurs» — коротко и по смыслу.
- **M2:** «Bepul mini-kurs sovg‘a qilamiz», «3 mln o‘rniga 0 so‘m», «faqat kun oxirigacha» на месте. ==bepul== — одно слово, перенос строки разметку не порвёт.
- **M3:** «Har kimga kurs:» — лозунговая модель «Har kimga …». «AI sari yo‘l» — как «treyding sari ilk qadam». «siz ham … o‘rgana olasiz» передаёт «можешь и ты».
- **M4:** «Kursda o‘rganing!» и «Faqat bugun soat 23:59 gacha bepul» — как «soat 20:30» в корпусе.
- **M5:** «Bepul!!» и «Oling» короче русских, на плашке читаются с первого взгляда.
- **M6:** «Uyda kompyuterda ishlashni xohlaysizmi?» — формула «…ni xohlaysizmi?». «AI-mutaxassis bo‘ling» влезает в дыру мема.
- **M7:** «Darslar to‘lovsiz ekan, olib qoling!» — оборот «…ekan, …» значит «пока…». «to‘lovsiz» не повторяет BEPUL с плашки.
- **2-1:** метки «Start / Pul / Yil o‘tib», «·» и двоеточия на местах. «rulda o‘tirgan soatga to‘lashadi» точно. «Hisob-kitob, va’da emas» — с тутуком ’.
- **2-1b:** «O‘qish bilan: mos keladi / mos kelmaydi» — одно слово на всю карусель. «haftasiga 2–3 kecha».
- **2-3:** «Birjasiz mijoz qayerdan topiladi» — безличное, без «?», как в оригинале. «10 ta kanaldan 3 tasi», «amakingiz do‘koni, do‘stingiz kafesi» — живо. Двоеточия совпадают с русскими, так что k_rows делит строки так же.
- **2-4:** «chetga ishlagani ketadi», «patent, ijara, ovqat», «Oiladan yillab uzoqda» — коротко. Третье лицо сохранено, правило Meta соблюдено.

---

## Как проверено

- **JSON валиден, UTF-8.** Набор ключей у v2 тот же, что у v1, у каруселей совпадение полное. Отличия в метаданных:
  - `len_check.over_20pct` пересчитан;
  - `m1_options[2].rank` стал «отброшен» вместо 3 — это вердикт по «O‘rgan|Ing».
- **Апострофы.** В текстах для картинок:
  - 132 знака ‘ (U+2018), все после o/g;
  - 1 тутук ’ (U+2019) — «va’da»;
  - 0 ASCII-апострофов `'`, 0 знаков ʻ и `.
  - 14 ASCII-апострофов остались только в дословных цитатах корпуса в `glossary` и `address_form`, как в v1. На картинки они не идут.
- **Обращение:** 0 местоимений и окончаний «sen». Все призывы на -ing/-ng, в вопросах -siz.
- **Термины:** AI-mutaxassis ×14, mini-kurs ×16, bepul ×30, Telegram ×5, so‘m ×22, $1000 ×17. Других написаний нет: «AI mutaxassis», «minikurs», «1000$», «som» и т. п.
- **Цифры и цены:** все числа в каждом креативе и карусели совпадают с v1.
- **Совместимость с рендером.** Все сборщики build.py (32 HTML) и video.py (V1, V2, M2 × 2 формата) отработали на данных v2 в памяти; файлы проекта не записывались. Карусели собираются в 6, 6, 6 и 4 карточки, как в v1. «·» и «:» в text_uz совпадают с v1 поштучно.
- **Пересчитанные метаданные.** len_check и alt_len посчитаны тем же способом, что в v1 (len(), порог >20%). В notes_uz изменённых креативов добавлен хвост «Редактор v2: …», в m1_options — вердикт, в about — описание v2.

## Что передать проверкам 2–3 и рендеру

- **M2, строка с ценой (`nowrap`, 110 px).** «3 mln so‘m → 0 so‘m» на 2 знака длиннее русской. Глазами проверить, что не вылезает за край 940 px.
- **«AI-mutaxassis»** оставлено по ТЗ. Литературная норма — изафет «AI mutaxassisi» (как «SMM mutaxassisi»). Если корректор решит менять, то во всех файлах разом, включая kw5 у V1.
- **Не сверено с живыми интерфейсами:** строка уведомления Uzum Bank «Karta to‘ldirildi» и узбекское название «Yandex Xaritalar».
- **Цитата в 2-3, карточка 2,** — перевод. Если Саидазим говорил по-узбекски, лучше поставить его дословные слова.
- **Имена файлов для рендера.** build.py и video.py читают `creatives_uz.json`, карусели — `creatives_uz_type2.json`. Финал после проверок 2–3 сохранить под этими именами. Сейчас `creatives_uz_type2.json` — это v1.
