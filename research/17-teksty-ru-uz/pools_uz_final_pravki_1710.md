# Правки 17.10.2026: формулировки носителя с креативов → тексты под постами

Носитель (Силбек) 15.10 и 17.10 вычитал узбекский текст **только на креативах**. Тексты под постами он ещё не читал. Те же обороты стояли и в подписях, и подпись спорила с картинкой. Поэтому его замены с креативов перенесены в подписи. Скрипт — `apply_native_fixes_1710.py`, повторный запуск ничего не меняет. Таблица «было → стало» по креативам — `research/16-kreativy-meta/АКТУАЛЬНЫЕ креативы УЗ — Meta/_АКТУАЛЬНО — прочитай первым.md`.

## Что заменено

| Было | Стало | Где | Образец носителя |
|---|---|---|---|
| ilk $1000 ga chiqish rejasi | ilk $1000 ni topish rejasi | P7 mid | I3-3: «2–3 oydayoq ilk $1000 ni toping» |
| $1000 ga chiqish rejasi | oyiga $1000 topish rejasi | P1, P2, P3, P4, P7, P9 — long | I3-1: «Sovg‘a: oyiga $1000 topish rejasi» |
| noldan oyiga $1000 ga chiqish yo‘li | noldan oyiga $1000 topish yo‘li | P1 long | I3-1, I1-2: «oyiga $1000 topish» |
| oyiga $1000 ga qanday chiqiladi? | oyiga $1000 qanday topiladi? | P1 mid | I2-1: «Masofadan oyiga $1000 qanday topiladi?» |
| ilk $1000 ga qanday chiqishni | ilk $1000 ni qanday topishni | P3 short | I2-3: «ilk $1000 ni qanday topishni» |
| ilk $1000 ga qanday chiqish | ilk $1000 ni qanday topish | P3 mid, P4 mid, P6 mid | I2-3 |
| 2 kechqurunda yasadim | 2 kunda yasadim | P9 short, mid, long | I3-2: «Bunday saytni 2 kunda…» |
| за 2 вечера (RU) | за 2 дня | P9 short, mid, long | русский исходник I1-3/I3-2 поменяли 17.10 |

Всего 16 замен в узбекском и 3 в русском. Эти же замены внесены в `03-ТЕКСТЫ-ПУЛЫ-UZ.md`. Пересобраны:
- `02-ТЕКСТЫ-ПУЛЫ-RU.md` — `build_pools.py`;
- `для-носителя/Тексты на проверку — UZ.xlsx` — `build_pack_uz.py`;
- `для-носителя/Тексты под постами RU-UZ — для Силбека.docx` — `build_docx_silbek.py`.

`check_uz.py pools_uz_final.json`: 0 ошибок, 0 предупреждений.

## Что не трогали

- **Срочность, зачёркнутая цена и счётчик мест** («3 mln so‘m», «kun oxirigacha», «100 ta joydan 26 tasi qoldi»). Вася 17.10 решил оставить как есть.
- **«Batafsil», «5 ta xizmat» в P2 long, пул 8 «bilak kuchi»** — по-прежнему в списке README «Что решить до запуска».
- **Копия текстов в `research/18-struktura-kampaniy-i-piksel/structure.json` (план 15.10)** осталась старой. Тексты для заливки берёт `research/19-zapusk-meta-bm/build_launch.py` прямо из `pools_uz_final.json`.

## Если Силбеку уже отправили docx

Если он правит docx, собранный 17.10 в 16:04, его вариант будет без этих 16 замен. Сверять по этой таблице или отправить ему новый docx.
