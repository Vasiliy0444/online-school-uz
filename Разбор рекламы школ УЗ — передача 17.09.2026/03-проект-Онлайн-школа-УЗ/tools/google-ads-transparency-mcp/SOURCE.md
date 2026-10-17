# Источник

- Репозиторий: https://github.com/block-town/google-ads-transparency-mcp
- Коммит: 8180b10a338be0d825d59797084df6bb8c06cca6 (09.09.2026, v0.3.0) — на дату копирования это HEAD
- Скопировано: 16.09.2026, без изменений. Не скопированы `scripts/socks_over_ssh.py` (SSH-туннель — не используем) и `uv.lock`
- Лицензия: MIT (файл LICENSE)
- Проверка безопасности 16.09.2026: весь код прочитан.
  - Сеть: adstransparency.google.com (главная ради куки + внутренние RPC `SearchService/SearchSuggestions`,
    `SearchService/SearchCreatives`, `LookupService/GetCreativeById`), превью креативов на googlesyndication.com
    и displayads, картинки на tpc.googlesyndication.com; видео — YouTube через внешнюю программу yt-dlp.
  - Внешние программы: только `frames.py` — yt-dlp, ffmpeg, ffprobe (список аргументов, без shell).
  - Диск: только файлы креативов и кадры в переданную папку; `server.py` пишет manifest.json.
  - Переменные окружения: `GOOGLE_ADS_TRANSPARENCY_PROXY`. Без неё читает файл
    `~/.config/google-ads-transparency/residential-proxy` и проверяет SOCKS на 127.0.0.1:1080.
  - Заголовки запросов как у браузера Chrome (User-Agent, sec-ch-ua). Подделки TLS-отпечатка нет.
  - На ответ 429, редирект /sorry/ и капчу выбрасывает `AdsTransparencyBlocked`, капчу не решает.
  - eval/exec, закодированных вставок, установщиков нет. Тесты в сеть не ходят.

## Как используется в проекте

Как MCP-сервер в Claude **не** зарегистрирован. Скрипты `research/05-razbor-konkurentov/` подключают пакет как библиотеку:

```python
import os, sys
os.environ["GOOGLE_ADS_TRANSPARENCY_PROXY"] = "direct"   # только прямое соединение — ставить ДО импорта клиента
sys.path.insert(0, str(TOOLS / "google-ads-transparency-mcp" / "src"))
from google_ads_transparency_mcp import GoogleAdsTransparency, AdsTransparencyBlocked
client = GoogleAdsTransparency(region="UZ", min_interval=2.0)   # UZ → код региона 2860
```

Окружение: `~/.venvs/gads-transparency` — только `requests==2.32.3` и `pytest` (пакет `mcp` не ставим, `server.py` не используем).
Тесты: `PYTHONPATH=src ~/.venvs/gads-transparency/bin/python -m pytest tests -q --ignore tests/test_server.py`.

## Что запрещаем

- Ротацию резидентных прокси и туннель: `GOOGLE_ADS_TRANSPARENCY_PROXY=direct` всегда.
- Обход блокировок: на `AdsTransparencyBlocked` — стоп, ждать и сообщить; прокси не подключать.
- Регистрацию MCP-сервера в конфиге Claude.

## Известные ограничения

- Регион подставляется только в список креативов (`get_creative_ids`); поиск рекламодателя и `ad_count` — по всему миру.
- `get_ad_detail` отдаёт только дату последнего показа; дату первого берём из сырых ответов `SearchCreatives` (номера полей проверяем на пилоте).
- `last_shown` считается в часовом поясе машины.
- `compare_advertisers` помечает `parent_entity`, если домен привёл к рекламодателю с другим названием — такие числа школе не приписываем.
- `extract_video_frames` забирает все `frame_*.jpg` в папке — каждому креативу своя папка.
