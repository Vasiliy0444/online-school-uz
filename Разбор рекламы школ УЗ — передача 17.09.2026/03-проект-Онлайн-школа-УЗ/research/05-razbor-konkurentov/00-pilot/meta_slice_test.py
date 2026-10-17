#!/usr/bin/env python3
"""Пилот: что делает фильтр start_date[min]/[max] на странице рекламодателя — делит выдачу по дате запуска
или оставляет всё, что показывалось в эти даты. Две загрузки с паузой, без прокрутки.

Запуск: ~/.venvs/fb-ads-library/bin/python meta_slice_test.py 111238895346791
"""
import json
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import meta_collect as mc  # noqa: E402

TZ = timezone(timedelta(hours=5))
WINDOWS = [("2026-04-01", "2026-04-30"), ("2026-09-01", "2026-09-16")]


def main() -> None:
    page_id = sys.argv[1]
    report = []
    for i, (lo, hi) in enumerate(WINDOWS):
        url = mc.library_url(search_type="page", view_all_page_id=page_id, **{"start_date[min]": lo, "start_date[max]": hi})
        result = mc.fetch(url)
        starts = sorted(datetime.fromtimestamp(a["start_date"], TZ).date().isoformat()
                        for a in result["ads"].values() if a.get("start_date"))
        row = {"window": f"{lo}..{hi}", "status": result["status_code"], "counter": result["counter_text"],
               "no_results": result["no_results"], "rate_limited": result["rate_limited"], "ads": len(result["ads"]),
               "start_min": starts[0] if starts else None, "start_max": starts[-1] if starts else None,
               "starts_inside_window": sum(lo <= s <= hi for s in starts)}
        report.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if result["rate_limited"]:
            print("RATE LIMIT — stop", flush=True)
            (HERE / "meta" / f"slice-test-{page_id}.json").write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                                                     encoding="utf-8")
            sys.exit(3)
        (HERE / "meta" / f"slice-{page_id}-{lo}-{hi}.json").write_text(
            json.dumps(result, ensure_ascii=False), encoding="utf-8")
        if i < len(WINDOWS) - 1:
            time.sleep(random.uniform(40, 60))
    (HERE / "meta" / f"slice-test-{page_id}.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
