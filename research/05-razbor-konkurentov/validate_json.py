#!/usr/bin/env python3
"""Проверка файлов разметки агентов по схемам (jsonschema).

  python3 validate_json.py tags 04-razbor/tags/qadam            — теги креативов (schemas/creative_tags.schema.json)
  python3 validate_json.py landing 04-razbor/landings/qadam     — разборы лендингов (schemas/landing.schema.json)
Печатает ошибки по файлам; код выхода 1, если есть ошибки.
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
SCHEMAS = {"tags": HERE / "schemas" / "creative_tags.schema.json", "landing": HERE / "schemas" / "landing.schema.json"}


def main() -> None:
    kind, folder = sys.argv[1], Path(sys.argv[2])
    validator = Draft202012Validator(json.loads(SCHEMAS[kind].read_text(encoding="utf-8")))
    bad = 0
    files = sorted(folder.glob("*.json"))
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"{path.name}: не JSON — {exc}")
            bad += 1
            continue
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        if errors:
            bad += 1
            for e in errors[:5]:
                print(f"{path.name}: {'/'.join(map(str, e.path)) or '(корень)'} — {e.message[:160]}")
    print(f"проверено {len(files)}, с ошибками {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
