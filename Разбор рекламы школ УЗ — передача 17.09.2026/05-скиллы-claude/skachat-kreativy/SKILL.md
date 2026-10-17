---
name: skachat-kreativy
description: >
  Сбор и скачивание рекламных креативов конкурентов из Meta Ad Library (и Google Ads Transparency Center) —
  только публичные страницы, без входа, без куки, прокси и обхода защиты. Использовать, когда нужно получить
  все активные объявления рекламодателя с картинками и видео, датами запуска, числом копий креатива и ссылками
  на лендинги. Проект: «Онлайн школа УЗ», раздел research/05-razbor-konkurentov.
---

# Скачать креативы конкурентов

Рабочие скрипты лежат в `~/Desktop/CURSOR/БИЗНЕС/Онлайн школа УЗ/research/05-razbor-konkurentov/`.
Проверено на пилоте 16.09.2026 — подробности в `00-pilot/ИТОГИ-ПИЛОТА.md`.

## Жёсткие правила

- Никаких аккаунтов, куки, прокси, stealth-режимов, подмены TLS-отпечатка и `navigator`.
  MetaAdsCollector не запускать: он подделывает отпечаток Chrome (`impersonate="chrome"`).
- Лимит или защита — сразу стоп, ничего не обходить: `Rate limit exceeded` у Meta, HTTP 429 / `google.com/sorry` / капча у Google,
  «вы не бот» у YouTube. Ждать и сообщить пользователю.
- К Meta — одно задание за раз, паузы 25–45 с между загрузками страниц, 2–4 с между файлами. Без прокрутки выдачи.
- Только публичные бизнес-данные. Креативы — чужая собственность: только для внутреннего анализа.
- Тяжёлые файлы — вне Рабочего стола (он синхронизируется с iCloud): `~/Data/online-shkola-uz/05-razbor-konkurentov/`.

## Meta Ad Library

1. **Найти ID страницы Ad Library.** Это `page_id` из JSON любого объявления рекламодателя или `view_all_page_id`
   в ссылке «все объявления». ID профиля (`facebook.com/<число>/`, колонка `handle` старого скана) не подходит —
   по нему выдача пустая. Быстрее всего — загрузить страницу любого его объявления:
   `~/.venvs/fb-ads-library/bin/python meta_collect.py ad --library-ids <id>` (или `--candidates`) — в документе
   сразу приходят `page_id`, до 30 объявлений этой страницы и счётчик «~N results».
2. **Поиск рекламодателей по словам:**
   `~/.venvs/fb-ads-library/bin/python meta_collect.py discover [--limit N]` — 124 запроса ниш заработка.
   С 16.09.2026 поиск по словам показывает только свежие запуски (≈ текущий месяц) — это дополнительный источник новичков,
   а не полный список рекламодателей.
3. **Страница рекламодателя:**
   `~/.venvs/fb-ads-library/bin/python meta_collect.py page --page-ids <id1,id2>` — счётчик активных объявлений
   в UZ и 30 самых показываемых (сортировка Meta по показам) с полным JSON.
4. **Все активные объявления страницы (больше 30):**
   `~/.venvs/fb-ads-library/bin/python meta_collect.py windows --page-id <id> --from-month YYYY-MM` — окна по месяцам
   с фильтром `start_date[min]/[max]`, окно со счётчиком больше 30 делится пополам; в конце — сверка объединения окон
   с общим счётчиком страницы.
5. **Скачать медиа сразу** (ссылки CDN подписаны и истекают):
   `python3 media_download.py --raw-dir ~/Data/online-shkola-uz/05-razbor-konkurentov/raw/meta/page --school <id> [--page-ids …]`
   — один файл на уникальный медиафайл, видео HD (иначе SD), превью, картинки, карточки каруселей; при истёкшей ссылке —
   yt-dlp по ссылке объявления. Журнал — `02-reklama/manifest_media_<school>.csv`.

Что есть в JSON объявления: `ad_archive_id`, `page_id`, `page_name`, `start_date`, `end_date`, `is_active`,
`collation_id`, `collation_count` (сколько объявлений используют креатив), `publisher_platform`,
`snapshot.display_format` (VIDEO / IMAGE / DCO / CAROUSEL), `snapshot.body.text`, `snapshot.cards[]`, `snapshot.videos[]`,
`snapshot.images[]`, `snapshot.link_url`, `snapshot.cta_text`, `snapshot.page_like_count`.
Показов и расходов по Узбекистану нет.

Документ страницы приходит с кодом 403 после короткой JS-проверки — это норма для любого браузера;
успех проверяем по числу разобранных объявлений.

## Google Ads Transparency Center

Библиотека `tools/google-ads-transparency-mcp` (как Python-пакет, MCP не регистрировать), окружение `~/.venvs/gads-transparency`:

```python
import os, sys
os.environ["GOOGLE_ADS_TRANSPARENCY_PROXY"] = "direct"      # до импорта клиента
sys.path.insert(0, "<проект>/tools/google-ads-transparency-mcp/src")
from google_ads_transparency_mcp import GoogleAdsTransparency, AdsTransparencyBlocked
client = GoogleAdsTransparency(region="UZ", min_interval=2.0)
rows = client.compare_advertisers(["domain.uz"])            # status: ok / absent / blocked / error; parent_entity — не приписывать
ids = client.get_creative_ids(advertiser_id, 100)            # регион UZ применяется здесь
detail = client.get_ad_detail(advertiser_id, creative_id)    # формат, last_shown, текст, image_url / video_url
```

Каждому креативу — своя папка (функция кадров забирает все `frame_*.jpg` в папке).
16.09.2026 Google отвечал нашему IP капчей на первом же запросе — сначала одна пробная попытка, при блокировке стоп.

## Хранение

```
~/Data/online-shkola-uz/05-razbor-konkurentov/
  raw/meta/{discover,page}/*.json         сырые загрузки (объявления + счётчик)
  kreativy/<school>/meta/<library_id>/    <library_id>_<slot>_<video_hd|video_sd|video_preview|image>.<ext>, frames/, audio.mp3
  kreativy/<school>/google/<creative_id>/
  logs/
```

## Проверки

- Счётчик «~N results» против числа собранных объявлений; вручную во встроенном браузере — на 3 школах.
- 20 случайных креативов: файл, начало текста и дата старта против страницы объявления `facebook.com/ads/library/?id=<id>`.
