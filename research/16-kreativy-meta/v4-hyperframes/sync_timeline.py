"""Подставляет timeline.json в index.html между маркерами /*TL-BEGIN*/ … /*TL-END*/.
timeline.json — единственный источник времени: его читают и картинка, и звук (sfx/cues)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
tl = json.loads((ROOT / "timeline.json").read_text(encoding="utf-8"))
html_path = ROOT / "index.html"
html = html_path.read_text(encoding="utf-8")
block = "/*TL-BEGIN*/ " + json.dumps(tl, ensure_ascii=False, separators=(",", ":")) + " /*TL-END*/"
new, n = re.subn(r"/\*TL-BEGIN\*/.*?/\*TL-END\*/", lambda _: block, html, flags=re.S)
if n != 1:
    raise SystemExit(f"маркеры TL-BEGIN/TL-END найдены {n} раз, нужно 1")
html_path.write_text(new, encoding="utf-8")
print("timeline.json → index.html: ok")
