"""Проверка правил разметки на реальных объявлениях из пробного прогона 15.09.2026.

Запуск из этой папки:  ~/.venvs/fb-ads-library/bin/python -m pytest test_classify.py -q
"""
from datetime import date

import classify as c

SHAHLO = ("Sun'iy intellekt haqida hamma gapiryapti — lekin undan qanday foydalanishni kam odam biladi. "
          "16–17-sentabr, soat 20:30 (Toshkent) — bepul onlayn vebinar. 2 kun ichida: AI bilan video yaratish, "
          "Claude yordamchisi va tayyor promptlar")
UZNETIX = ("Internetda pul ishlashning qonuniy usuli. ⚡ Darrov ogohlantirib qo‘yamiz: qisqa vaqt ichida katta "
           "boylik orttirib bo‘lmaydi. Lekin qo‘shimcha oylik daromad olish mumkin. Bu usul investitsiya deb ataladi.")
BANK = ("💸 Visa Start Sum kartasi endi daromad keltiradi! Har bir to‘lov uchun 0,5% keshbek oling Va kartaning "
        "boshqa afzalliklaridan ham foydalaning")
TAXI = ("🚖 Oyiga 10–15 mln so‘mgacha daromad olishni xohlaysizmi? MyTaxi haydovchisiga aylaning va yaqin vaqt "
        "ichida buyurtmalarni qabul qilishni boshlang.")
COURIER = ("🟡 Yandex Dostavka’da kuryer bo‘lib ish boshlang va daromad qiling! 🔹 Ishlash tartibini o‘rgatamiz "
           "va tushuntiramiz")
UZSELLER = ("💰Xitoydan mahsulot tanlab onlayn savdoga olib kirishni o'rgatamiz Bugun marketplace’lar orqali savdo "
            "qilish — yangi imkoniyatlar eshigi. Ozon, Uzum, Wildberries, Yandex Market va boshqa platformalarda")
MYFXBRO = ("O'zingizni 1$ dollaringizni ham xavfga qo'ymasdan 10,000$ lik real hisobda treyd qilishni xohlaysizmi? "
           "Myfxbro jamoasi siz uchun uch oylik onlayn kurs tayyorladi ✅ Treyding sohasini 0 dan 100 gacha to'liq")
MOBILOGRAF = ("📱 ONLAYN MOBILOGRAFIYA KURSIMGA YANA START BERDIM! 🚀 Telefoningiz orqali professional video olishni, "
              "chiroyli montaj qilishni va mobilografiyadan daromad topishni o‘rganishni xohlaysizmi?")
ALI = "Onlayn daromad qilish uchun manga obuna bo’ling va kurs so’zini qoldiiring"
DENTAL = ("Vebinar: Level up — elaynerlarda ochiq va chuqur tishlashni tuzatishda intruziya va ekstruziya "
          "Sizni xalqaro ekspert bilan onlayn-uchrashuvga taklif qilamiz")
RUSSIAN = "Бесплатный вебинар для тех, кто хочет зарабатывать на маркетплейсах. Узнайте, как начать уже сейчас"
UZ_CYRILLIC = "Бепул вебинар: маркетплейсда қандай савдо қилиш мумкин? Рўйхатдан ўтинг ва дарсларни олинг"


def test_language_detection():
    assert c.detect_lang(SHAHLO) == "uz-lat"
    assert c.detect_lang(UZSELLER) == "uz-lat"
    assert c.detect_lang(UZ_CYRILLIC) == "uz-cyr"
    assert c.detect_lang(RUSSIAN) == "ru"


def test_courses_are_info_products():
    for text in (SHAHLO, UZSELLER, MYFXBRO, MOBILOGRAF, ALI):
        assert c.info_score(text) >= 1, text[:40]


def test_jobs_banks_and_apps_are_not_info_products():
    for text in (BANK, TAXI, COURIER):
        assert c.info_score(text) == 0, text[:40]


def test_landing_domain_counts_as_webinar_signal():
    assert c.info_score(UZNETIX + " vebinar uznetix com") >= 1
    assert c.classify_funnel(UZNETIX + " vebinar uznetix com", "Learn More", "vebinar.uznetix.com")[0] == \
        "вебинар или бесплатный урок"


def test_funnel_types():
    assert c.classify_funnel(SHAHLO, None, "aiochiqdars.aicreator.academy")[0] == "вебинар или бесплатный урок"
    assert "слово в директ или комментарий" in c.classify_funnel(ALI, "Send message", "www.instagram.com")
    assert "слово в директ или комментарий" in c.classify_funnel(MOBILOGRAF, None, "www.instagram.com")
    assert "Telegram-бот или канал" in c.classify_funnel("Kanalga o'ting", None, "t.me")
    assert "заявка или звонок" in c.classify_funnel("Kurs haqida", "Apply now", "example.uz")


def test_niches():
    assert c.classify_niches(SHAHLO, ["voronki"])[0] == "ИИ"
    assert c.classify_niches(UZSELLER, ["zarabotok"])[0] == "маркетплейсы"
    assert c.classify_niches(MOBILOGRAF, ["zarabotok"])[0] == "монтаж и видео"
    assert c.classify_niches(MYFXBRO, ["zarabotok"])[0] == "бизнес и финансы"
    assert c.classify_niches(DENTAL, ["voronki"])[0] == "медицина и профобучение"
    assert c.classify_niches("Hech narsa", ["montazh"]) == ["монтаж и видео"]


def test_risk_flag():
    assert c.is_risky(MYFXBRO)
    assert c.is_risky(UZNETIX + " Ya’ni siz O‘zbekiston va Amerika kompaniyalarining aksiyalarini sotib olib, qimmatroq sotishingiz mumkin.")
    assert not c.is_risky(MOBILOGRAF)


def test_risk_false_positives_found_by_manual_review():
    trader = "Qanday Qilib TOP 5% Treyderlar Qatoriga Kirish Mumkin? Esingizdami, birinchi marta treyd qilgan kuningiz?"
    assert c.is_risky(trader)
    assert c.classify_niches(trader, ["voronki"])[0] == "бизнес и финансы"
    assert not c.is_risky("Ingliz tili kursi — o'zingizga investitsiya kiriting, kelajak uchun eng yaxshi qaror")
    assert not c.is_risky("KOMPYUTER, PLATFORMALAR VA REAL TRADING: brokerlar bilan ishlash, dispetcher kasbi")
    assert c.info_score("Bellissimo franshizasi: investitsiya kapitaliga ega hamkorlarni qidiramiz, o'rgatamiz") == 0


def test_prices():
    assert c.parse_prices_uzs("Kurs narxi 1 500 000 so'm, chegirma bilan 990 ming so'm") == [990_000, 1_500_000]
    assert c.parse_prices_uzs("Hammasi atigi $100") == [100 * c.USD_TO_UZS]
    assert c.parse_prices_uzs("Narxi 250 000 so‘m") == [250_000]


def test_income_promises_are_not_prices():
    prices, incomes = c.parse_money("Maqsadingiz — oyiga $1000+ daromad topish bo‘lsa, kursga keling")
    assert prices == []
    assert incomes == [1000 * c.USD_TO_UZS]
    prices, incomes = c.parse_money(TAXI)
    assert prices == [] and incomes == [15_000_000]


SHAMS = ("🔥 YANGI GURUHGA QABUL BOSHLANDI! Endi kurs dasturimizga SUN’IY INTELLEKT bo‘yicha darslar ham qo‘shiladi! "
         "📱 Instagram’da shaxsiy blog yuritishni 🎥 Mobilografiya va videografiyani 📈 SMM va kontent-meykerlikni "
         "🤖 Sun’iy intellektdan kontent yaratishda foydalanishni o‘rganib")
MAFTOONE = ("🎯 1 ta kurs orqali 3 ta kasb mutaxassisiga aylaning! 45 kunlik maxsus oflayn darsimda siz: - 0 dan "
            "Mobilografiya bilimlari. Barchasi expert bilan bemalol ishlash darajasigacha o'rgatiladi. "
            "Barcha darslar oflayn tarzda shaxsan o'zim tomonimdan o'tiladi.")
DR_RAW = ("Soha mutaxassislari diqqatiga Siz uchun 2 kunlik bepul vebinar tashkil qilyapmiz 0:00 / 0:59 "
          "[](https://l.facebook.com/l.php?u=https%3A%2F%2Fgavhar-darvish.firstcoder.uz%2Findex3.html%3Ftaxid%3D552333&h=AUD8) ​ Active")
ALI_RAW = ("Onlayn daromad qilish uchun manga obuna bo’ling va kurs so’zini qoldiiring 0:00 / 0:54  WWW.INSTAGRAM.COM Ali "
           "Send message  See more System status   * [Ad Library API](https://www.facebook.com/ads/library/api/) "
           "[English (US)](https://www.facebook.com/language/)")


def test_clean_body_removes_links_timers_and_footer():
    assert "taxid" not in c.clean_body(DR_RAW)
    assert "0:59" not in c.clean_body(DR_RAW)
    assert "English" not in c.clean_body(ALI_RAW)
    assert c.info_score(c.clean_body(DR_RAW)) >= 1


def test_course_subject_beats_bonus_ai_module():
    assert c.classify_niches(SHAMS, ["montazh"])[0] == "монтаж и видео"
    assert "медицина и профобучение" not in c.classify_niches(MAFTOONE, ["montazh"])
    assert "языки" not in c.classify_niches(c.clean_body(ALI_RAW), ["zarabotok"])


def test_promotions_shops_and_vacancies_are_not_courses():
    bank = "📢 «Omadli Marafon» davom etmoqda! Asakabank Mastercard kartalari orqali har kuni xaridlarni amalga oshiring va sovrinlarni qo‘lga kiriting"
    shop = "iPhone 17 olmoqchi bo‘lsangiz, shoshilmang 👀 Biz bu haqida bepul video dars tayyorladik"
    vacancy = "Registon maktabi rus tilida dars o'ta oladigan matematika, ingliz tili fanlari o'qituvchilarini qidirmoqda"
    for text in (bank, shop, vacancy):
        assert c.info_score(text) == 0, text[:30]
    assert c.info_score("Toshkent shahridagi filiallarimizda nemis tilini o'rganishni boshlang! 2 ta ustoz bilan dars") >= 1


def test_other_education_niches():
    cases = {
        "[BEPUL] Ingiliz tili bo’yicha C1 olish sirlari, 9 yillik tajribaga ega o‘qituvchi": "языки",
        "Kimyo va Biologiyadan milliy sertifikatga tayyorlanayotganlar diqqatiga! 3 oylik intensiv kurs": "школа, дети, поступление",
        "🔥 QOMAT RESEPTI — 15 kunlik marafon! sog‘lom ozish yo‘lida. Narxi: 99 000 so‘m": "здоровье и похудение",
        "MASTER-KLASS | 7-POTOK Sizni yangi retseptlar va eng mazali natijalar kutmoqda": "ремёсла и бьюти",
        "#buxgalteriya #kurs #soliq #dars Glavbux School": "бухгалтерия и офис",
        "Haydovchilik imtihonidan o‘tolmayapmisiz? Atigi 7 kunda intensiv kurs": "другие профессии",
    }
    for text, niche in cases.items():
        assert c.classify_niches(text, ["voronki"])[0] == niche, text[:40]


def test_started_date_formats():
    assert c.parse_started("Sep 10, 2026") == date(2026, 9, 10)
    assert c.parse_started("8 Sept 2026") == date(2026, 9, 8)
    assert c.parse_started(None) is None
