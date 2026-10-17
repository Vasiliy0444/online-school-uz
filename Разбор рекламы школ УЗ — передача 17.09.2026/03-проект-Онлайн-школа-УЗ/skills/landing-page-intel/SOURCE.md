# Источник

- Репозиторий: https://github.com/gooseworks-ai/goose-skills
- Путь: skills/competitive-intel/capabilities/landing-page-intel
- Коммит: e1592ee2bdc563e3aa6e36b308bcd88f393e3817
- Скопировано: 15.09.2026, без изменений файлов скилла
- Лицензия: MIT (файл LICENSE рядом)
- Проверка безопасности 15.09.2026: все файлы прочитаны целиком, скрытых инструкций нет.

## Оговорки

- Скрипт: `python3 ~/.claude/skills/landing-page-intel/scripts/scrape_landing_page.py --url <URL>` (в SKILL.md путь указан относительно репозитория goose-skills). Нужен пакет requests.
- Скрипт делает только GET-запросы к указанному сайту и печатает JSON. Шаблоны технологий заточены под англоязычный B2B SaaS — для узбекских лендингов полезнее блоки CTA, заголовков и соцдоказательств.
- Сайты, которые рендерятся только JavaScript'ом (Tilda-подобные, SPA), через requests отдают мало — смотреть их встроенным браузером.
