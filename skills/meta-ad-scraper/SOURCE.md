# Источник

- Репозиторий: https://github.com/gooseworks-ai/goose-skills
- Путь: skills/ads/capabilities/meta-ad-scraper
- Коммит: e1592ee2bdc563e3aa6e36b308bcd88f393e3817
- Скопировано: 15.09.2026, без изменений файлов скилла
- Лицензия: MIT (файл LICENSE рядом)
- Проверка безопасности 15.09.2026: все файлы прочитаны целиком, скрытых инструкций нет.

## Оговорки

- Запасной путь сбора через Apify-актор apify~facebook-ads-scraper. Платно: по SKILL.md ~$5 за 1 000 объявлений. Ключ APIFY_API_TOKEN лежит в ~/.claude/.env.
- Скрипт: `source ~/.claude/.env && python3 ~/.claude/skills/meta-ad-scraper/scripts/search_meta_ads.py --company "<запрос>" --country UZ`.
- НЕ задавать переменные GOOSEWORKS_API_KEY и GOOSEWORKS_API_BASE: с ними запросы идут через сторонний прокси api.gooseworks.ai.
- Упомянутого в SKILL.md файла references/apify-config.md в репозитории на этом коммите нет.
- Для Узбекистана основной путь — бесплатный сборщик facebook-ads-library-mcp; Apify только если он перестанет работать.
