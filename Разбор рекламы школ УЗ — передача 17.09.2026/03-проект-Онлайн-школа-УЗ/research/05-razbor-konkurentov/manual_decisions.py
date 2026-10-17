#!/usr/bin/env python3
"""Ручные решения по рекламодателям (разбор 16.09.2026 по категории страницы Meta, доменам и текстам объявлений)
→ 01-master/schools_manual.csv. Применяются в schools_build.py поверх автоматической склейки.

track: заработок | английский | языки (другие) | исключить: <причина>
Имена сопоставляются с page_name из 01-master/pages.csv точно (после обрезки пробелов).
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = HERE / "01-master"

# school_id: (названия страниц, отображаемое имя, трек, ниша, основание)
DECISIONS = {
    "najot-talim": (["Najot Ta'lim", "Najot Ta'lim talabalari"], "Najot Ta'lim", "заработок", "IT, ИИ, мобилография",
                    "учебный центр IT и цифровых профессий, офлайн-филиалы + онлайн; вторая страница — видеоинтервью учеников "
                    "с основателем Temurbek Adhamov (тексты прямо называют курсы Najot Ta'lim)"),
    "qadam": (["Qadam.online"], "Qadam Education (Qadam.online)", "заработок", "маркетплейсы", "обучение продажам на Uzum, своя платформа"),
    "shahlo-alikhanova": (["Shahlo.alikhanova"], "Shahlo Alikhanova (AI Creator Academy)", "заработок", "ИИ и доход", "блогер, запуски через бесплатный видеоурок"),
    "ibrahim-gulyamov": (["IbrahimGulyamov"], "Ibrahim Gulyamov", "заработок", "бизнес", "интенсивы для владельцев бизнеса по регионам (B2B)"),
    "it-house": (["IT House Education"], "IT House Education", "заработок", "IT и компьютерная грамотность", "учебный центр"),
    "aipply": (["Aipply Academy"], "Aipply Academy", "заработок", "ИИ и компьютерная грамотность", "курс «Kompyuter savodxonligi + AI»"),
    "space-academy": (["Space Academy"], "Space Academy", "заработок", "мобилография и SMM", "школа мобилографии"),
    "bir-group": (["Yo'ldosh Yusupov"], "Bir Group (Yo'ldosh Yusupov)", "заработок", "цифровые профессии", "продюсер: бесплатное обучение 7 профессиям → вебинар"),
    "logist-academy": (["Logist Academy Declaration", "Logist Academy", "Logist Academy - Uzbekistan"], "Logist Academy", "заработок",
                       "логистика США", "три страницы одного бренда: декларирование, диспетчер, Instagram logist_academy"),
    "leo-logist": (["Leo Logist"], "Leo Logist", "заработок", "логистика США", "шогирдлик-академия логистики; английский — требование, не предмет"),
    "proweb": (["Proweb - It o’quv markazi"], "Proweb", "заработок", "IT, монтаж", "IT-центр, бесплатные открытые уроки"),
    "geeks-andijan": (["Geeks Andijan"], "Geeks Andijan", "заработок", "IT, мобилография", "региональный центр (Андижан)"),
    "pdp-academy": (["PDP Academy"], "PDP Academy", "заработок", "программирование", "IT-академия"),
    "interno": (["interno.school.uz", "Interno Management School"], "INTERNO School", "заработок", "дизайн интерьера, ИИ",
                "офлайн-курсы; вторая страница ведёт на тот же лендинг interno-school.vercel.app"),
    "holitech-ai": (["Agancy Meta Ads"], "Holitech AI («Agancy Meta Ads»)", "заработок", "ИИ + YouTube", "мастер-класс «оyiga 1000$»"),
    "munojat-safarboyeva": (["Munojat Safarboyeva"], "Munojat Safarboyeva", "заработок", "мобилография", "онлайн-курс блогера"),
    "uzum-sellers": (["Uzum Sellers"], "Uzum Academy (Uzum Sellers)", "заработок", "маркетплейсы", "академия площадки Uzum"),
    "fintechhub": (["Fintech"], "Fintechhub", "заработок", "программирование, кибербезопасность", "IT-школа"),
    "top-mentors": (["Top Mentors- educational system"], "Top Mentors", "заработок", "маркетинг", "маркетинг для застройщиков + обучение (B2B)"),
    "school-21": (["Школа цифровых технологий School 21"], "School 21", "исключить: бесплатная программа", "IT", "бесплатное обучение — нет платного продукта"),
    "rivojuz": (["Talantlar Maktabi 2026"], "RivojUz («Talantlar Maktabi 2026»)", "исключить: бесплатная программа", "SMM, маркетинг",
                "бесплатный офлайн-курс для выпускников и безработных"),
    "hbs-academy": (["HBS academy Uzbekistan"], "HBS academy Uzbekistan", "заработок", "трейдинг и инвестиции", "зона риска"),
    "myfxbro": (["Myfxbro"], "Myfxbro", "заработок", "трейдинг", "зона риска"),
    "mjcompanyuz": (["Mjcompanyuz"], "Mjcompanyuz", "заработок", "трейдинг", "зона риска"),
    "englify": (["Englify School"], "Englify School", "английский", "английский", "онлайн-школа + приложение"),
    "inter-nation": (["Inter Nation English School", "INTER Nation Andijan", "INTER Nation Samarkand"], "Inter Nation English School",
                     "английский", "английский", "школа английского; филиалы Андижан и Самарканд ведут на тот же домен inter-nation.uz"),
    "thompson-english": (["Thompson English School"], "Thompson English School", "английский", "английский, IELTS", "школа английского"),
    "sirojiddin": (["Sirojiddin teacher"], "Sirojiddin teacher (IELTS)", "английский", "IELTS", "преподаватель-блогер, лендинг на vercel"),
    "barno-askarova": (["Barno Askarova"], "Barno Askarova (LinguaBarno)", "английский", "английский", "преподаватель-блогер, вебинар на vercel"),
    "prep-uz": (["Prep.uz"], "Prep.uz", "языки (другие)", "русский язык, тесты", "подготовка к тестам, не английский"),
    "blitz": (["Blitz nemis tili markazi"], "Blitz", "языки (другие)", "немецкий", "центр немецкого"),
    "grand-talim": (["Grand Ta'lim"], "Grand Ta'lim", "языки (другие)", "арабский", "центр арабского"),
    "progress-online": (["Progress Online School"], "Progress Online School", "языки (другие)", "арабский", "онлайн арабский"),
    "wildberries": (["Wildberries.uz"], "Wildberries.uz", "исключить: не школа", "", "маркетплейс, реклама WB Taxi с кэшбэком"),
    "idu": (["International Digital University"], "International Digital University", "исключить: вуз", "", "университет"),
    "renessans": (["Renessans  university"], "Renessans University", "исключить: вуз", "", "университет"),
    "oxu": (["Osiyo Xalqaro Universiteti Buxoro"], "Osiyo Xalqaro Universiteti", "исключить: вуз", "", "университет"),
    "thompson-schools": (["Thompson Maktablari"], "Thompson Maktablari", "исключить: школа для детей", "", "частная общеобразовательная школа"),
    "robbit": (["Robbit akademiyasi - Robototexnika va Dasturlash"], "Robbit", "исключить: дети", "", "робототехника 9–15 лет"),
    "protochka": (["Protochka.uz"], "Protochka.uz", "исключить: магазин", "", "электроника"),
    "dona": (["Dona"], "Dona", "исключить: магазин", "", "приложение розничной торговли"),
    "psychologist": (["abdurahmonova_sitorabonu"], "abdurahmonova_sitorabonu", "исключить: психология", "", "курсы отношений для женщин"),
    "skillbox": (["Skillbox Узбекистан"], "Skillbox Узбекистан", "исключить: русскоязычная реклама", "IT", "объявления в основном на русском"),
    "edu-tizim": (["EDU Tizim"], "EduTizim", "исключить: не школа", "", "CRM-система для учебных центров («O‘quv markazingiz bormi? Unda sizga EduTizim kerak»)"),
}


def main() -> None:
    with (M / "pages.csv").open(encoding="utf-8") as fh:
        by_name: dict[str, list[str]] = {}
        for p in csv.DictReader(fh):
            by_name.setdefault(p["page_name"].strip(), []).append(p["page_id"])
    rows, missing = [], []
    for school_id, (names, display, track, niche, note) in DECISIONS.items():
        page_ids = [pid for n in names for pid in by_name.get(n.strip(), [])]
        if not page_ids:
            missing.append(display)
            continue
        rows.append({"school_id": school_id, "page_ids": "; ".join(page_ids), "name": display, "track": track, "niche": niche, "note": note})
    with (M / "schools_manual.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"решений: {len(DECISIONS)}, записано: {len(rows)}, не найдено страниц: {missing}")


if __name__ == "__main__":
    main()
