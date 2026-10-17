# ТЗ: пиксель Meta, Conversions API и сквозная аналитика — мини-курс УЗ

Для агента-техтаря. Версия 15.10.2026.
- Словарь событий в машинном виде — `events.json` рядом.
- Что и на какое событие оптимизирует реклама — `01-СТРУКТУРА-КАМПАНИЙ.md`.
- Почему так — `00-РЕСЕРЧ-НАСТРОЕК.md`.

---

## 0. Что нужно получить

1. Meta видит каждого человека от клика до оплаты. Группы объявлений оптимизируются на **`CompleteRegistration` = старт бота**.
2. В нашей базе у каждого человека лежит **ID объявления**, с которого он пришёл, и все его шаги. По ним MCP считает цену каждого шага по объявлению, креативу и группе — независимо от окна атрибуции Meta.
3. **Что отслеживаем:**
   - клики и визиты;
   - все клики по странице;
   - нажатие «Начать»;
   - регистрацию (старт бота);
   - изучение бота: уроки, медали, задание;
   - канал;
   - запись на практику, переход, приход, оффер, запись урока;
   - страницу курса, «Оплатить», покупку.

## 1. Границы

- Реклама не запускается, живые объекты в Meta не меняются.
- **Секреты** — только в переменных окружения сервера. Не в репозиторий, не в чат, не в лог.
- **Лендинг** — репозиторий `Vasiliy0444/ii-na-zakaz-mini`, локально `websites/ii-na-zakaz-mini/`:
  - `index.html` собирается из `src/index.src.html` командой `python3 scripts/build.py`, руками его не править;
  - перед публикацией — `node --test tests/*.test.mjs`, `node scripts/check-texts.mjs`, `python3 scripts/qa.py`.
- **Страница курса** (`npopko55-cmd/ii-na-zakaz`) принадлежит Никите — менять только с его согласия.
- **Сквозной тест** с телефонов (Instagram → лендинг → бот) проходит Вася. Агент проверяет события в Test Events и в базе.
- **Персональные данные.** Закон УЗ требует хранить данные граждан на серверах в Узбекистане (ст. 27-1). Где лежит база шлюза — решить с юристом до запуска. В таблицу аналитики — только агрегаты без персональных данных.

## 2. Как связаны части

```
Реклама Meta ──(fbclid + UTM + ad_id в ссылке)──▶ Лендинг (GitHub Pages)
   │                                                 │ пиксель: PageView, ViewContent, BlockView, FaqOpen, ClickElement, Lead
   │                                                 │ sendBeacon ──▶ ШЛЮЗ  POST /s  (сессия: sid, vid, fbc, fbp, UTM, ad_id; IP и UA — из запроса)
   │                                                 ▼
   │                         кнопка «Начать» → tg://resolve?domain=<бот>&start=vm-<sid>-<ad_id>  (запасная: https://t.me/…)
   │                                                 ▼
   │                                   Бот: /start vm-<sid>-<ad_id> ──▶ ШЛЮЗ POST /e  CompleteRegistration
   │                                        уроки, медали, задание, канал, запись ──▶ POST /e
   │                                        личная ссылка ──▶ ШЛЮЗ GET /go/practice ──▶ Комната практики (пиксель + пульс POST /room/beat)
   │                                        кнопка оплаты ──▶ страница курса ?uid= (пиксель: ViewContent, InitiateCheckout, Contact)
   │                                                                     ▼
   │                                        Tribute / менеджер ──▶ POST /e  Purchase
   ▼
ШЛЮЗ ──▶ Meta Conversions API (/{PIXEL_ID}/events)   и   база: sessions, leads, events, practice, orders
```

**Шлюз** — один небольшой сервер. Он принимает сессии и события, хранит базу и шлёт события в Meta. Если бот работает на своём сервере — ставим шлюз туда же.

## 3. Идентификаторы

| ID | Что это | Где живёт | Правило |
|---|---|---|---|
| `vid` | постоянный ID посетителя | localStorage `mini_vid` + cookie на 365 дней | 16 знаков, только строчные латинские буквы и цифры (base36): пиксель и сервер должны хешировать одну и ту же строку. Создаётся при первом заходе |
| `sid` | ID визита | sessionStorage `mini_sid` | 12 знаков base36 (строчные и цифры). Новый, если в адресе есть UTM или `fbclid` либо `sid` ещё нет |
| `page_load_id` | ID загрузки страницы | память страницы | случайный, для `event_id` у PageView |
| `ad_id` | ID объявления Meta | параметр `aid` в ссылке рекламы (`{{ad.id}}`) | только цифры. Также `asid` — группа, `cid` — кампания, `pl` — плейсмент |
| `fbc` | клик-ID Meta | cookie `_fbc` + localStorage | `fb.1.<время первого появления fbclid, мс>.<fbclid>`. **Регистр fbclid не менять.** Если `_fbc` уже есть с тем же fbclid — брать её |
| `fbp` | браузерный ID Meta | cookie `_fbp`, ставит пиксель | передавать как есть |
| `start` | метка для бота | ссылка на бота | `vm-<sid>-<ad_id>` или `vm-<sid>` без `ad_id`. ≤64 знаков, только `A-Z a-z 0-9 _ -` |
| `tg_id` | Telegram ID | бот | — |
| `external_id` | общий ID человека для Meta | все события | на лендинге `[vid]`, в боте и дальше `[vid, tg_id]`. На сервере — SHA-256, пиксель хеширует сам |
| `uid` | ID лида для страницы курса | ссылка из бота `?uid=` | непрозрачный токен лида, не Telegram ID |

Текущая метка лендинга `vm-<source>-<campaign>-<content>` (`js/attribution.js`) меняется на `vm-<sid>-<ad_id>`. UTM бот получает из шлюза. `utm_content` в адресе остаётся — по нему лендинг меняет заголовок (`js/hooks.js`).

## 4. Шаг 1 — активы Meta

1. **Датасет и пиксель** «UZ mini-course»: Events Manager → «Подключить данные» → «Веб». По справке CLI есть `meta ads dataset create` (не проверено). ID — в переменную `META_PIXEL_ID`.
2. **Настройки пикселя:**
   - «Автоматические события» — **выключить**: у пикселей с 03.08.2026 они включены по умолчанию и дадут дубли;
   - «Отслеживать события без кода» — выключить;
   - cookie первой стороны — **включить**, без них не будет `_fbp` и `_fbc`;
   - автоматический расширенный подбор (advanced matching) — включить.
3. **Подтверждение домена:**
   - лучше свой домен: DNS TXT, лендинг и шлюз на нём (`api.<домен>`);
   - если остаёмся на GitHub Pages — meta-тег на корне `vasiliy0444.github.io`, для этого нужен репозиторий `vasiliy0444.github.io` с `index.html`.
   - `event_source_url` у website-событий должен быть на подтверждённом домене.
4. **Токен CAPI:** Events Manager → датасет → «Настройки» → Conversions API → «Создать токен доступа» или системный пользователь с доступом к датасету. Переменная `META_CAPI_TOKEN`. Это не токен MCP из `infra/meta-ads/`.
5. **Test Events:** код тестовых событий — в `META_TEST_EVENT_CODE`, только на время проверки.
6. **Часовой пояс рекламного кабинета** — Asia/Tashkent.

## 5. Шаг 2 — лендинг

1. **Пиксель** — базовый код из Events Manager в `<head>` (`src/index.src.html`). `fbq('init', PIXEL_ID, {external_id: vid})`. Строку базового кода `fbq('track', 'PageView')` заменить на `fbq('track', 'PageView', {}, {eventID: 'pv_' + page_load_id})`, иначе браузерный PageView не склеится с серверным.
2. **ID** — `vid`, `sid`, `page_load_id`, `fbc` по таблице раздела 3.
3. **Сессия в шлюз** — при загрузке `navigator.sendBeacon(GATEWAY + '/s', JSON)` с полями:
   - `sid`, `vid`, `page_load_id`, `fbc`, `fbp`;
   - `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`;
   - `cid`, `asid`, `aid`, `pl`;
   - `landing_url` (полный `location.href`), `referrer`, `ts_ms`.
   - Повторить отправку при клике «Начать»: `_fbp` иногда появляется после первой отправки.
   - Тело — строка JSON в `Blob` с типом `text/plain`: такой запрос на другой домен уходит без предзапроса CORS. Если `sendBeacon` недоступен — `fetch(url, {method: 'POST', body, keepalive: true, mode: 'no-cors'})`. Шлюз разбирает JSON при любом `Content-Type`.
4. **Мост `dataLayer` → пиксель.** Сейчас `main.js` пишет события в `window.dataLayer`, их надо дублировать в `fbq`:

   | Событие в `dataLayer` | Событие пикселя | `eventID` | Серверная копия |
   |---|---|---|---|
   | `page_view` | `PageView` | `pv_<page_load_id>` | шлюз шлёт сам при получении `/s` |
   | 50% прокрутки или 15 сек — добавить | `ViewContent` `{content_name:'landing_engaged'}` | `vc_<sid>` | `POST /e` |
   | `block_view` | `BlockView` `{block, id}` (`trackCustom`) | `bv_<sid>_<block>` | нет |
   | `faq_open` | `FaqOpen` `{item}` (`trackCustom`) | `faq_<sid>_<item>` | нет |
   | `cta_click` | `Lead` `{place, hook}`, первый за визит | `lead_<sid>` | `POST /e` |
   | клик по другому `[data-track]` | `ClickElement` `{element, block, label}` (`trackCustom`) | `ce_<sid>_<n>` | нет |

5. **Кнопки «Начать»:**
   - метка `start` = `vm-<sid>` + `-<aid>`, если `aid` — цифры;
   - `href` = `https://t.me/<бот>?start=<метка>`;
   - по клику: пиксель `Lead` + beacon в `/e`, затем `location = 'tg://resolve?domain=<бот>&start=<метка>'`; если через ~700 мс страница ещё видна — переход по `https`-ссылке.
   - Встроенный браузер Instagram часто не открывает приложение по `t.me` (ресёрч 10.10, п. 9.5). Какой вариант работает лучше — решает тест на iPhone и Android (раздел 12, п. 13).
6. **Перед запуском** (это задача CURSOR-iom3, не техтаря, но без неё запуска нет):
   - узбекская версия лендинга;
   - страница политики;
   - строка о согласии рядом с кнопкой.
7. **Политика безопасности страницы (CSP)**, если её добавят: разрешить `connect.facebook.net`, `www.facebook.com` и домен шлюза.

## 6. Шаг 3 — шлюз

### Точки входа

| Метод | Путь | Кто вызывает | Что делает |
|---|---|---|---|
| POST | `/s` | лендинг (публично) | сохраняет сессию; IP — из `X-Forwarded-For` (первый адрес) или адреса соединения, UA — из заголовка; один раз на `page_load_id` шлёт `PageView` в CAPI |
| POST | `/e` | лендинг — только `Lead`, `ViewContent`, `RecordingView` и только с `sid`; бот, комната, оплата — с заголовком `X-Gateway-Key` | принимает событие, дополняет данными сессии, пишет в базу, шлёт в CAPI |
| GET | `/go/practice?t=<токен>` | человек из бота | токен = HMAC от `{tg_id, practice_date, срок действия 3 дня}`; пишет `PracticeJoinClick`, 302 на комнату `?t=<токен>` |
| POST | `/room/beat` | страница комнаты раз в 60 сек | копит минуты; на 5-й минуте — `PracticeAttend`, в минуту оффера — `PracticeOffer`, оба по разу |
| GET | `/stats?from=&to=` | аналитика (MCP-отчёт), с ключом | агрегаты по дню регистрации и `ad_id`: старты, уроки, задание, запись, приход, оффер, «Оплатить», покупки, выручка — без персональных данных. Формат — `03-АНАЛИТИКА-ЧЕРЕЗ-MCP.md`, раздел 7 |
| GET | `/health` | мониторинг | 200 |

- Публичные точки: ограничение частоты по IP. Проверка длины и символов полей. Список разрешённых имён событий.
- Публичный `/e` принимает событие, только если `sid` уже есть в `sessions`, сессии меньше суток и `event_id` построен из этого `sid` (`lead_<sid>`, `vc_<sid>`). Иначе кто угодно накрутит конверсии.
- CORS: для `fetch`-запросов разрешить только домен лендинга, страницы комнаты и страницы курса.
- Повторный `event_id` в базе — событие не шлём второй раз.

### База

| Таблица | Поля |
|---|---|
| `sessions` | sid (PK), vid, page_load_id, fbclid, fbc, fbp, utm_source, utm_medium, utm_campaign, utm_term, utm_content, cid, asid, aid, pl, landing_url, referrer, ip, ua, created_at |
| `leads` | tg_id (PK), vid, sid, ad_id, adset_id, campaign_id, utm_content, hook, has_sid, first_start_at, uid (токен для страницы курса) |
| `events` | event_id (PK), event_name, tg_id, vid, sid, event_time, action_source, payload, capi_status, capi_response, sent_at |
| `practice` | tg_id, practice_date, booked_at, join_click_at, minutes, attended, offer_seen, recording_minutes |
| `orders` | order_id (PK), tg_id, tariff, value_uzs, value_usd, cbu_rate, paid_at, method, installments, installment_no |

### Отправка в Meta

- `POST https://graph.facebook.com/<актуальная версия>/{META_PIXEL_ID}/events`.
- Пачкой до 1000 событий, не позже минуты после события.
- Повтор 3 раза с паузой на 5xx и таймаутах. Ответ (`events_received`, `fbtrace_id`) — в `events.capi_response`.
- **Хеширование SHA-256** (hex) после `trim` и нижнего регистра:
  - `external_id`, `country` (`uz`);
  - `ph` — цифры с кодом страны, `998XXXXXXXXX`, если телефон дали с согласием;
  - `em`.
  - Не хешировать: `fbc`, `fbp`, `client_ip_address`, `client_user_agent`.
- **Дополнение:** событие с `tg_id` → лид → `sid` → сессия. Из сессии берём `fbc`, `fbp`, IP, UA, `landing_url`, `ad_id` и кладём в `user_data` и `custom_data`.
- **`action_source`:**
  - **`CompleteRegistration` — `website`.** `event_source_url` = `landing_url` сессии, `client_ip_address` и `client_user_agent` — из сессии лендинга. Регистрация начата на сайте, так событие гарантированно годится для оптимизации группы с местом конверсии «Сайт».
  - **События внутри бота — `chat`** («мессенджер» в документации Meta).
  - **Если приёмка покажет, что `chat`-события не собирают аудитории** — перевести их в `website` тем же способом. Решить до запуска: история событий между источниками не переносится.
- **`event_time`** — UTC в секундах, момент действия, не момент отправки. Старше 7 дней Meta не примет.
- **Переменные окружения:** `META_PIXEL_ID`, `META_CAPI_TOKEN`, `META_TEST_EVENT_CODE` (только для тестов), `GATEWAY_KEY`, `HMAC_SECRET`, `DB_URL`, `BOT_USERNAME`, `PRACTICE_ROOM_URL`.

### Пример — регистрация

```json
POST https://graph.facebook.com/<версия>/{META_PIXEL_ID}/events?access_token={META_CAPI_TOKEN}
{
  "data": [{
    "event_name": "CompleteRegistration",
    "event_time": 1792087041,
    "event_id": "reg_123456789",
    "action_source": "website",
    "event_source_url": "https://<лендинг>/?utm_source=meta&utm_content=I1-1_l1_math&aid=23851234567890123",
    "user_data": {
      "external_id": ["<sha256(vid)>", "<sha256(tg_id)>"],
      "fbc": "fb.1.1792086980123.IwZXh0bgNhZW0BMABh...",
      "fbp": "fb.1.1792086979001.1234567890",
      "client_ip_address": "<IP из сессии>",
      "client_user_agent": "<UA из сессии>",
      "country": ["<sha256('uz')>"]
    },
    "custom_data": {"content_name": "bot_start", "sid": "ab3de6gh9jk2", "ad_id": "23851234567890123", "hook": "math"}
  }],
  "test_event_code": "<только при проверке>"
}
```

### Пример — событие из бота

```json
{
  "event_name": "Lesson3Done",
  "event_time": 1792260000,
  "event_id": "l3done_123456789",
  "action_source": "chat",
  "user_data": {"external_id": ["<sha256(vid)>", "<sha256(tg_id)>"], "fbc": "<из сессии>", "fbp": "<из сессии>", "country": ["<sha256('uz')>"]},
  "custom_data": {"companies": 3}
}
```

## 7. Шаг 4 — бот

1. **`/start`:**
   - Разбор метки: `^vm-([a-z0-9]{12})(?:-(\d{5,25}))?$`.
   - Первый старт этого `tg_id` с найденной сессией → лид + `POST /e CompleteRegistration`, `event_id = reg_<tg_id>`.
   - Повторный `/start` в Meta не шлём.
   - Сессии нет, но в метке есть `ad_id` → лид с `ad_id`. В Meta шлём `chat`-событием с одним `external_id`: для `website` нужен UA из браузера.
   - Метки нет → лид с `has_sid=false`, в Meta не шлём (`BotStartDirect` — только база).
2. **Шаги в боте** (события 8–13 из `events.json`) — в момент действия:
   - бот выдал урок N → `LessonOpen` (lesson=N);
   - медаль → `BotMedal`;
   - принял задание «3 компании» → `Lesson3Done`;
   - проверил подписку на канал → `ChannelJoin`;
   - человек выбрал время практики → `PracticeBooked`.
3. **Личная ссылка на практику** в напоминаниях и в момент начала: `https://<шлюз>/go/practice?t=<токен>`.
4. **Кодовые слова.** Если практика идёт не в нашей комнате, а в трансляции Telegram или YouTube:
   - слово в начале → `PracticeAttend` (`mode=code_word`);
   - слово в конце → `PracticeOffer`.
5. **Кнопка оплаты** ведёт на страницу курса: `?uid=<токен лида>&ref=<...>`. Режим «из бота» на странице Никиты уже читает `uid` и `ref`.
6. **Если бот на конструкторе** — те же события через его вебхуки в `POST /e` с ключом.

## 8. Шаг 5 — комната практики

Площадка не выбрана. Предлагаю свою страницу `/practice/` на нашем домене с плеером: урок 4 по сценарию — автовебинар, ссылка с YouTube или запись. Так видно приход, минуту ухода и момент оффера.
- Страница читает `t` из адреса. Пиксель: `PageView` с `external_id`.
- Пока вкладка видна — `POST /room/beat {t, minute}` раз в 60 секунд.
- Минута оффера — в настройке расписания практики.
- Запись урока — `/recording/`, на 5-й минуте просмотра — `RecordingView`.
- Если выберут трансляцию в Telegram или YouTube — только личная ссылка и кодовые слова (раздел 7, п. 4).

## 9. Шаг 6 — страница курса (только с согласия Никиты)

- Тот же пиксель. `fbq('init', PIXEL_ID, {external_id: uid})`.
- События:
  - `PageView`;
  - `ViewContent` `{content_name:'course_page'}`;
  - `InitiateCheckout` `{value: <цена тарифа в USD>, currency:'USD', content_name:<тариф>, value_uzs}` на `tariff_click` и `pay_click`;
  - `Contact` на `manager_click`.
- Серверные копии — по желанию, через `POST /e` с `uid`.

## 10. Шаг 7 — оплата

- **Tribute:** спросить у поддержки API или вебхук, где есть Telegram ID покупателя и номер заказа. Официальной документации мы не нашли. Есть — обработчик → `POST /e Purchase`.
- **Нет вебхука или оплата частями через «Актив»:** менеджер в течение суток отмечает оплату в админке шлюза. Поля: `order_id`, Telegram, тариф, сумма в сумах, время оплаты, способ, число платежей.
  - Скрипт шлёт `Purchase`, `event_id = order_<order_id>`. `value` — **полная цена заказа** в USD по курсу ЦБ на день оплаты, сумма в сумах — в `value_uzs`.
  - Второй платёж — `InstallmentPaid`, не `Purchase`: иначе один заказ посчитается дважды.
- `event_time` — время оплаты. Отметка позже 7 дней не пройдёт, поэтому отмечать надо в тот же день.

## 11. Шаг 8 — Events Manager

### Custom conversions — на каждое своё событие

| Имя | Правило | Зачем |
|---|---|---|
| `CC_LANDING_ENGAGED` | `ViewContent`, content_name = landing_engaged | отделить от просмотра страницы курса |
| `CC_BLOCK_FINAL` | `BlockView`, block = final | дочитал до последнего блока |
| `CC_FAQ` | `FaqOpen` | — |
| `CC_LEAD_HERO`, `_PROGRAM`, `_FINAL`, `_FAQ`, `_DOCK` | `Lead`, place = … | какая кнопка работает |
| `CC_LESSON1`, `CC_LESSON2`, `CC_LESSON3` | `LessonOpen`, lesson = N | глубина изучения бота |
| `CC_L3DONE` | `Lesson3Done` | — |
| `CC_CHANNEL` | `ChannelJoin` | — |
| `CC_BOOKED` | `PracticeBooked` | будущая оптимизация (C7) |
| `CC_JOINCLICK` | `PracticeJoinClick` | — |
| `CC_ATTEND` | `PracticeAttend` | цена человека на практике |
| `CC_OFFER` | `PracticeOffer` | — |
| `CC_RECORDING` | `RecordingView` | — |
| `CC_COURSE_VIEW` | `ViewContent`, content_name = course_page | — |

- Это 19 из 100 возможных. Свои события пикселя в Insights иначе сливаются в одну строку.
- Создавать в Events Manager → «Пользовательские конверсии» или через Graph API `POST /act_<ID>/customconversions`. У MCP такого инструмента нет.

### Свои аудитории

Список и правила — `01-СТРУКТУРА-КАМПАНИЙ.md`, раздел 9. Создать **до первого показа**: через MCP `ads_create_custom_audience` или в Ads Manager.

## 12. Шаг 9 — приёмка

Перед проверкой включить `META_TEST_EVENT_CODE` и открыть Test Events.

| # | Действие | Что должно быть |
|---|---|---|
| 1 | Открыть лендинг с `?utm_source=meta&utm_content=I1-1_l1_math&aid=23851234567890123&fbclid=<тест>` | `PageView` из браузера и с сервера склеены (один `event_id`); есть `fbc` и `fbp`; заголовок — под хук `math` |
| 2 | Прокрутить до середины | `ViewContent` landing_engaged, браузер + сервер, склеены |
| 3 | Открыть вопрос, кликнуть по другим элементам | `FaqOpen`, `BlockView`, `ClickElement` с параметрами |
| 4 | Нажать «Начать» | `Lead` с `place`, склеен; Telegram открылся с `start=vm-<sid>-23851234567890123` (≤64 знаков) |
| 5 | Вася жмёт Start в боте | `CompleteRegistration` с сервера ≤10 сек. `action_source=website`, `event_source_url` на подтверждённом домене, есть `fbc`, `fbp`, IP, UA, два `external_id`. Второй `/start` нового события не даёт |
| 6 | Урок 1, медаль, задание, канал, запись на практику | `LessonOpen` lesson=1, `BotMedal`, `Lesson3Done`, `ChannelJoin`, `PracticeBooked` (`chat`) |
| 7 | Личная ссылка → комната → 5 минут → минута оффера | `PracticeJoinClick`, `PracticeAttend`, `PracticeOffer` — по одному |
| 8 | Страница курса из бота → тариф → менеджер | `ViewContent` course_page, `InitiateCheckout` с `value` в USD, `Contact` |
| 9 | Тестовая оплата или отметка менеджера, потом второй платёж | `Purchase` один раз, `value` — полная цена заказа; на второй платёж — только `InstallmentPaid` |
| 10 | Проверка `chat`-событий | события видны в обзоре датасета; custom conversion `CC_L3DONE` считает; тестовая своя аудитория на `LessonOpen` создаётся. Если аудитория не создаётся — перевести события бота в `website` до запуска |
| 11 | База | у лида есть `ad_id`, `adset_id`, `campaign_id`, `hook`; на каждый шаг — строка в `events`; старты без `sid` считаются отдельно |
| 12 | Insights | `meta ads insights get --ad-id <ID> --fields actions,cost_per_action_type --date-preset today` возвращает регистрацию и `offsite_conversion.custom.<ID>`. Точные строки `action_type` записать в таблицу соответствий |
| 13 | Телефоны (Вася) | iPhone и Android: превью рекламы в Instagram → лендинг → Telegram открывается → старт бота. Записать, какой вариант ссылки сработал (`tg://` или `https`) |
| 14 | После живого трафика | качество совпадения (EMQ) у `CompleteRegistration` ≥6; в диагностике датасета нет ошибок «Missing parameter» |

## 13. Что вернуть

1. ID датасета/пикселя, статус подтверждения домена, адрес шлюза, имена переменных окружения (без значений).
2. Таблица соответствий: событие → где стреляет → правило `event_id` → ID custom conversion → `action_type` в Insights.
3. ID своих аудиторий (`CA_*`).
4. Лог приёмки по разделу 12: скриншоты Test Events и EMQ.
5. Список отклонений от ТЗ с причинами.

## 14. Порядок работ

1. Активы Meta и пиксель (раздел 4).
2. Шлюз и база (раздел 6).
3. Лендинг (раздел 5).
4. Бот (раздел 7). Сначала выяснить, на чём он собран и кто его ведёт.
5. Комната практики (раздел 8) — когда выберут площадку.
6. Страница курса (раздел 9) — после согласия Никиты.
7. Оплата (раздел 10) — после ответа Tribute.
8. Custom conversions и аудитории (раздел 11).
9. Приёмка (раздел 12). Без пунктов 1–5, 10 и 13 рекламу не включаем.
