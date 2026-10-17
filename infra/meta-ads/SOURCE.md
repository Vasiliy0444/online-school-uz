# Происхождение локальной инфраструктуры

Официальный Meta Ads MCP: `https://mcp.facebook.com/ads`. Его размещает Meta; мы не копировали реализацию и не размещали прокси-сервер. [Обзор Meta](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/ads-mcp-server-overview).

Установлен **meta-ads==1.2.0** из PyPI в `/Users/Bel-a/.venvs/meta-ads-codex`. Официальная документация Meta прямо ссылается на этот PyPI-пакет. Наличие названия пакета само по себе не было основанием доверия. [Инструкция Meta](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/setup/get-started), [пакет](https://pypi.org/project/meta-ads/), [метаданные релиза](https://pypi.org/pypi/meta-ads/1.2.0/json).

Использован CPython **3.13.5** из `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13`; Meta требует Python **3.12+**. [Локальная проверка](../../research/15-meta-ads-avtomatizatsiya/verification.json), [требования Meta](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/setup/get-started).

Основной wheel: [meta_ads-1.2.0-cp313-cp313-macosx_11_0_arm64.whl](https://files.pythonhosted.org/packages/60/09/dde98f6d1d8ddaa0a15d83ce791930ed9c46be6da3231d14f7e1ba513c4f/meta_ads-1.2.0-cp313-cp313-macosx_11_0_arm64.whl). SHA-256 из [PyPI release metadata](https://pypi.org/pypi/meta-ads/1.2.0/json): `aa72bec860d4deb81eac257d659202ca7ccb781e138a2f56c4e13fa7a08618a8`.

Точные версии установленных зависимостей сохранены в [requirements.lock](requirements.lock). Это фиксация локального окружения, не lockfile с хешами всех транзитивных пакетов. Часть CLI поставляется скомпилированной; полного аудита его исходного кода мы не делали. Проверены происхождение по официальной ссылке, установленная версия, help нужной команды и ограниченный локальный wrapper. Живой API-сценарий **не проверен**. [Журнал](../../research/15-meta-ads-avtomatizatsiya/verification.json).

`credentials.py`, `prepare_creative.py` и тесты написаны в рамках этой задачи. Они не являются кодом Meta. Хранилище токена отделено от проекта; helper создаёт только одиночный креатив, без запуска рекламы. [Код хранения](credentials.py), [код подготовки](prepare_creative.py), [тесты](test_preparation.py).

Подключение `http_headers_helper` и фильтрация инструментов основаны на [справочнике конфигурации Codex](https://developers.openai.com/codex/config-reference/). Имена инструментов взяты из [публичной документации Meta](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/ads-mcp-server-tools-ad-creation-and-management); актуальная авторизованная схема для кабинета пока **не проверена**.
