# Источник

- Репозиторий: https://github.com/RamsesAguirre777/facebook-ads-library-mcp
- Коммит: ea3c877855c16fb4594f640634d06f85e414eadb (29.08.2026)
- Скопировано: 15.09.2026, без изменений
- Лицензия: MIT (файл LICENSE)
- Проверка безопасности 15.09.2026: весь код прочитан. Сеть — только страницы facebook.com/ads/library через headless Chromium (crawl4ai). На диск не пишет. Ключей и аккаунтов не требует.

## Как используется в проекте

Как MCP-сервер в Claude не зарегистрирован. Скрипт скана `research/03-reklama-meta/sweep.py` импортирует
из `facebook_ads_mcp_complete.py` две функции: `_render_ad_library` (рендер страницы) и
`_parse_ad_library_markdown` (разбор карточек объявлений).

Окружение: `~/.venvs/fb-ads-library` (вне папки проекта, чтобы не класть сотни мегабайт на Desktop).
Chromium: кеш Playwright `~/Library/Caches/ms-playwright`.

## Известные ограничения (из документации автора)

- Facebook отвечает headless-браузеру кодом 403, но отдаёт карточки — успех судим по разобранным карточкам.
- Разбор завязан на англоязычную разметку страницы: «Library ID», «Started running on», «Sponsored».
- Поле platforms обычно пустое (иконки, а не текст). Расходов и показов нет.
