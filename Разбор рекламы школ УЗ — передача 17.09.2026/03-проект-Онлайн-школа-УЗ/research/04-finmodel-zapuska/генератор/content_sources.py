"""Источники стартовых значений: лист «Источники цифр» и колонка «Источник» на главном листе."""

BRIEF_URL = "https://claude.ai/artifact/RGUpxwR5Sn9F54wb1Eq5Hb"

# key строки листа 1, подпись (None — как в модели), бенчмарк, гео, источники (до 4), дата, уверенность
SOURCES = [
    ("fx", None, "ЦБ РУз: 11 765,21 сум за $ на 15.09.2026; в I полугодии 2026 — 11 935–12 320", "UZ",
     ["https://cbu.uz/ru/arkhiv-kursov-valyut/json/USD/",
      "https://uz.kursiv.media/2026-08-28/dollar-snova-poshel-vverh-kurs-na-2-sentyabrya-vyros-do-11-820-sumov/"],
     "15.09.2026", "высокая"),
    ("price_cold", None, "Цены конкурентов в УЗ: IT 21–255 $, SMM 42–212 $, фриланс 170–595 $, ИИ-академии 255–510 $; "
     "базовый чек брифа — 2,5 млн сум ≈ 212 $. Чек 300 $ — по ответу заказчика", "UZ",
     [BRIEF_URL, "https://www.moxieschool.uz/", "https://sensorika.academy/", "https://brains.uz/kurslar/social-media-marketing/"],
     "15.09.2026", "средняя"),
    ("cpm", None, "Meta в УЗ: CPM 1–3 $ на широкую аудиторию; в Instagram 3–8 $; у другого агентства 0,5–2 $", "UZ",
     ["https://aksanov.digital/blog/meta-ads/skolko-stoit-reklama", "https://101digital.uz/en/blog/targeted-advertising-uzbekistan/",
      "https://www.xyzlab.com/meta-ads-benchmarks/uzbekistan", "https://unika-agency.com/blog/targetirovannaya-reklama-uzbekistan"],
     "2026", "низкая-средняя"),
    ("ctr", None, "Хороший CTR в Instagram УЗ — 1,5–3% (агентство); CTR Telegram Ads в кейсе курса — 0,98% (РФ)", "UZ / RU",
     ["https://101digital.uz/en/blog/targeted-advertising-uzbekistan/",
      "https://vc.ru/marketing/2878535-telegram-ads-dlya-onlajn-kursov-kesj-shkoly-nejronavykov"], "2026", "низкая-средняя"),
    ("cr_reg", None, "Со страницы регистрации регистрируются 80–90% (гайд); с Telegram Ads на бота подписываются 19–21% "
     "кликнувших (кейс курса). Для Meta → лендинг → бот берём ниже", "RU",
     ["https://vc.ru/id972483/798734-dohodimost-do-vebinara-kakoi-procent-optimalnyi",
      "https://vc.ru/marketing/2878535-telegram-ads-dlya-onlajn-kursov-kesj-shkoly-nejronavykov"], "2023–2026", "средняя"),
    ("cpl", None, "Лид в образовании УЗ — 2,3–3,6 $; CPL Meta в УЗ — 1–15 $, в сезон июль–сентябрь 10–12 $ (практик); "
     "база брифа — 6 $; кейс вебинара СНГ — 2,61 $", "UZ / СНГ",
     ["https://aksanov.digital/blog/meta-ads/analiz-kampaniy", "https://unika-agency.com/blog/targetirovannaya-reklama-uzbekistan",
      "https://t.me/s/targetologi_uz", "https://vc.ru/marketing/358361-keis-8141-registraciya-na-vebinar-dlya-onlain-shkoly-treidinga"],
     "2021–2026", "низкая-средняя"),
    ("att1", None, "Регистрация → эфир: в среднем 15–20% (РФ, 2026); 20–30% — норма, 50% — хорошо (гайд СНГ, 2023); "
     "в брифе база 35%", "RU / СНГ",
     ["https://www.sostav.ru/blogs/287076/96331", "https://vc.ru/id972483/798734-dohodimost-do-vebinara-kakoi-procent-optimalnyi",
      BRIEF_URL], "2023–2026", "средняя"),
    ("ap_rate", None, "Со вебинара покупают 5–20% зрителей (РФ). В брифе база: заявки — 12% участников, из них оплачивают 40%. "
     "Доли автооплат и броней отдельно не нашли — оценка", "RU",
     ["https://skillspace.ru/blog/kak-proviesti-prodaiushchii-viebinar-s-nulia-poshaghovyi-ghaid-dlia-ekspiertov-i-onlain-shkol-na-primierie-platformy-skillspace/",
      BRIEF_URL], "2025–2026", "низкая"),
    ("m_bk", None, "Заказ → оплата: 66,8% (вся платформа GetCourse, пик декабря 2025); 46% в примере финмодели школы; "
     "в исходном файле — 80%", "RU",
     ["https://getcourse.ru/magazine/analitika_2025",
      "https://noboring-finance.ru/gazeta/finmodel-onlajn-shkoly-kak-postroit-i-shablon/"], "2024–2026", "высокая"),
    ("m_or", None, "Звонок → оплата 50–55% по гайду (не проверено, пересказ в отчёте брифа); база брифа — 40%; "
     "в исходном файле — 40–50%", "RU", [BRIEF_URL], "2026", "низкая"),
    ("ai_pay", None, "ИИ-продавец: конверсия в чате выросла с ~10–12% до 25% за месяц (кейс самого вендора, B2B). "
     "Сколько даёт дожим в УЗ — не проверено, ставки ИИ — оценка", "RU",
     ["https://sellergpt.ru/blog/keyc-kak-my-uvelichili-konversiyu-v-messendzherakh-na-25-s-pomoshchyu-ii-sotrudnika"],
     "07.2025", "низкая"),
    ("ch_churn", None, "Отписки 8–12% подписчиков (РФ, период не указан); по отпискам после запуска данных нет", "RU",
     ["https://vc.ru/telegram/1425019-kak-poschitat-okupaemost-telegram-kanala"], "08.2024", "низкая"),
    ("w_reg_ch_rate", None, "Пост за 15 дней видят 36–44% подписчиков блогов, в маркетинге и tech — 7–10%. "
     "Серия анонсов охватывает больше одного поста; у каналов конкурентов в УЗ 300–4 000 подписчиков (бриф)", "RU / UZ",
     ["https://telesputnik.ru/materials/trends/news/issledovanie-kak-menyaetsya-vovlecennost-auditorii-v-telegram-v-zavisimosti-ot-razmera-kanala",
      BRIEF_URL], "2025–2026", "средняя"),
    ("w_att1", None, "Холодный марафон: день 1 — 25%, день 2 — 14% регистраций. Тёплый: день 1 — 68%, на день 2 "
     "вернулись 72% пришедших", "RU",
     ["https://vc.ru/marketing/2878535-telegram-ads-dlya-onlajn-kursov-kesj-shkoly-nejronavykov",
      "https://vc.ru/marketing/363540-anatomiya-analitiki-marafonnyh-mehanik-dlya-onlain-shkol"], "2022–2026", "низкая-средняя"),
    ("w_cpl", None, "Telegram-посевы в УЗ: подписчик 7–12 тыс. сум (0,59–1,02 $), клик 0,08–0,17 $ (агентство, май 2026); "
     "подписчик Telegram Ads — 0,15–1,5 €", "UZ",
     ["https://telegrad.uz/blog/skolko-stoit-reklama-v-telegram.html", "https://aksanov.digital/blog/telegram-ads/prodvigaem-kanal"],
     "2026", "средняя"),
    ("pay_partner", None, "Рассрочка 0% на 6–12 мес через Uzum и Alif Nasiya — стандарт рынка УЗ (бриф). "
     "Alif одобряет 50–60% заявок, Uzum Nasiya — до 97%. С 01.01.2027 ПП-294: максимум 12 мес", "UZ",
     [BRIEF_URL, "https://www.spot.uz/ru/2025/07/11/bnpl-regulation/", "https://uzum.uz/media/kak-ustroen-servis-rassrochki-uzum-nasiya/",
      "https://yuz.uz/ru/news/rassrochka-pod-0-pochemu-posle-pp-294-polovina-takix-predlojeniy-yuridicheski-stanet-kreditom"],
     "2025–2026", "средняя"),
    ("partner_fee", None, "Комиссию школы у Uzum и Alif найти не удалось (бриф). Если 0% для покупателя, наценку платит школа; "
     "покупателю наценка на 12 мес — 27–44%. Ориентир РФ (Prodamus): 8,5% / 10% / 15% за 3 / 6 / 12 мес", "UZ / RU",
     [BRIEF_URL, "https://www.gazeta.uz/ru/2025/07/02/nasiya-bnpl/", "https://prodamus.ru/chastyami"], "2025–2026", "низкая"),
    ("own_default", None, "Данных по невыплатам нет. Оценка ресёрча: первый платёж 30%, не доплачивают 15% остатка; "
     "школа выходит в ноль после 3–4 из 12 платежей (РФ)", "RU",
     ["https://blog.whiteedtech.ru/blog/vnutrennyaya-rassrochka-ot-shkoly-kak-ee-organizovat/"], "03.2024", "низкая"),
    ("acq", None, "Payme / Click / Uzum: комиссия 0,8–2%, подключение ~2 недели, только местным юрлицам; UzQR — 0,65%", "UZ",
     ["https://uzneo.uz/blog/payme-click-uzum-podklyuchit-oplatu", "https://vc.ru/dev/3069312",
      "https://www.gazeta.uz/ru/2026/06/23/uzar-tariff/"], "2026", "средняя-высокая"),
    ("refund", None, "Возвраты 5% — допущение брифа; данных по Узбекистану нет", "—", [BRIEF_URL], "15.09.2026", "низкая"),
    ("ai_setup", None, "Разработка ИИ-бота в УЗ — 5–25 млн сум (пакеты 10 / 20 / 35 млн); ИИ и хостинг — 0,3–3 млн сум в месяц", "UZ",
     ["https://innosoft.uz/blog/ai-narxi-2026"], "07.2026", "средняя"),
    ("ai_dialog_cost", None, "Сервисы берут 5–30 ₽ за диалог (только сниппет поиска, не проверено); на своём боте токены дешевле", "RU",
     ["https://botseller.ai/blog/telegram-bot-dlya-prodazh"], "2025–2026", "низкая"),
    ("m_pct", None, "Затраты на продажи 10% выручки — допущение брифа", "—", [BRIEF_URL], "15.09.2026", "низкая"),
    ("m_salary", None, "Оклад, команда и сервисы — оценка, уточнить у своей команды", "—", [], "—", "низкая"),
    ("curator", None, "Кураторы на ученика: 10 / 15 / 25 $ при чеке 85 / 212 / 425 $ — допущение брифа", "—", [BRIEF_URL],
     "15.09.2026", "низкая"),
    ("tax", None, "ООО: налог с оборота 4% до 1 млрд сум в год (≈ 85 тыс. $); выше — НДС 12% и налог на прибыль 15%; "
     "ИП и самозанятые — 1%", "UZ",
     ["https://buxgalter.uz/publish/doc/text205224", "https://www.spot.uz/ru/2025/11/26/taxes-for-2026/",
      "https://buxgalter.uz/publish/doc/text212712_nk-2026_izmeneniya_po_nalogu_s_oborota_dlya_ip_i_samozanyatyh"],
     "2026", "высокая"),
    ("div_tax", None, "Дивиденды нерезиденту — 10%, для России по договору тоже 10%. На общем режиме до кармана доходит "
     "≈ 76,5 $ со 100 $ прибыли (бриф)", "UZ",
     ["https://taxsummaries.pwc.com/republic-of-uzbekistan/corporate/withholding-taxes", BRIEF_URL], "16.01.2026", "высокая"),
    ("one_time_other", None, "Госпошлина за регистрацию ООО — 300 тыс. сум ≈ 25 $; принимать оплату массовой аудитории можно "
     "только через своё ООО (бриф)", "UZ",
     ["https://azma.uz/tpost/jlz2jkvtx1-gosposhlina-za-registratsiyu-ooo", BRIEF_URL], "2026", "средняя"),
]

# строки главного листа, которые берут ссылку из другой строки источников
SOURCE_ALIAS = {"w_att2": "w_att1", "own_first": "own_default", "ai_sub": "ai_setup", "team": "m_salary",
                "services": "m_salary", "bk_rate": "ap_rate", "or_rate": "ap_rate"}
