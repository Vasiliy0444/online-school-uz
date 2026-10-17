# Meta Ads: локальная подготовка

Выбран официальный Meta-hosted MCP и официальный CLI для локальных медиа. Авторизация и операции реального кабинета ещё **не проверены**.

- [Исследование и решение](../../research/15-meta-ads-avtomatizatsiya/ИТОГ.md)
- [Пошаговый план подключения](../../research/15-meta-ads-avtomatizatsiya/ПЛАН-ПОДКЛЮЧЕНИЯ.md)
- [Шаблон ТЗ](../../research/15-meta-ads-avtomatizatsiya/ТЗ-ШАБЛОН.md)
- [Происхождение CLI](SOURCE.md)
- [Журнал проверки](../../research/15-meta-ads-avtomatizatsiya/verification.json)

Токен сохраняется только через скрытый интерактивный ввод:

```sh
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 infra/meta-ads/credentials.py store
```

Проверка локального creative JSON без API:

```sh
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 infra/meta-ads/prepare_creative.py --spec /absolute/path/creative.json --preview
```

Без `--preview` команда выполняет запись в Meta и требует токен и выданное ТЗ. Фиксирован `PAUSED`; автоматических повторов нет. Helper поддерживает одиночное изображение либо видео. Он не реализует кампании, группы, объявления и все остальные форматы: их подготовка предусмотрена через MCP после проверки фактических схем.

Офлайн-проверки:

```sh
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 -B -m unittest discover -s infra/meta-ads -p 'test_*.py' -v
```

Не выводить в чат `credentials.py headers`, access token, App Secret и содержимое чужих MCP-конфигураций. Сохранять ответы/manifest без секретов. При timeout сначала сверять фактически созданные объекты.
