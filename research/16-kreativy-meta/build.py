"""Сборка HTML-макетов креативов по дизайн-системам (superdesign/design_system/*.json).

python3 build.py --lang uz|ru [--only I2-1,M1] [--render]
HTML кладётся в superdesign/design_iterations/, PNG — в render/<lang>/.
"""
import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
PHOTOS = Path("/Users/Bel-a/Desktop/Фото Никиты спикера")
CUT = ROOT / "assets" / "cutouts"
ASSETS = ROOT / "assets"
OUT_HTML = ROOT / "superdesign" / "design_iterations"
FORMATS = {"story": (1080, 1920), "feed": (1080, 1350)}

FONTS = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:wght@400;500;600;700;800;900"
    "&family=Roboto+Condensed:wght@400;500;700;800"
    "&family=Courier+Prime:wght@400;700"
    "&family=Montserrat:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,600;1,700;1,800;1,900"
    "&family=Montserrat+Alternates:wght@600;700;800"
    "&family=Roboto:wght@300;400;500;700;900"
    "&family=Caveat:wght@500;600;700"
    "&family=PT+Serif:wght@400;700"
    "&display=block"
)

FIT_JS = """
<script>
function contentH(el){
  const gap = parseFloat(getComputedStyle(el).rowGap) || 0; const kids = Array.from(el.children);
  return kids.reduce((s, k) => s + k.getBoundingClientRect().height, 0) + gap * Math.max(0, kids.length - 1);
}
function fitCol(el){
  const max = el.clientHeight; let fs = parseFloat(getComputedStyle(el).fontSize); let g = 0;
  while (contentH(el) > max - 24 && g < 90) { fs *= 0.97; el.style.fontSize = fs + 'px'; g++; }
}
function fitBox(el){
  const maxh = parseFloat(el.dataset.maxh || 1e9); const maxw = parseFloat(el.dataset.maxw || 1e9);
  let fs = parseFloat(getComputedStyle(el).fontSize); let g = 0;
  while ((el.offsetHeight > maxh + 1 || el.scrollWidth > maxw + 1) && g < 90) { fs *= 0.97; el.style.fontSize = fs + 'px'; g++; }
}
function fillBelow(){
  const hw = document.querySelector('.headwrap'); const img = document.querySelector('img[data-fill]');
  if (!hw || !img) return;
  const [x0, y0, x1, y1, iw, ih, cx, drop, maxh] = img.dataset.fill.split(',').map(Number);
  const H = document.body.clientHeight; const top = hw.getBoundingClientRect().bottom + 36;
  const contentH = Math.min(maxh, H - top + drop); const sc = contentH / (y1 - y0);
  img.style.width = (iw * sc) + 'px'; img.style.top = (H + drop - contentH - y0 * sc) + 'px'; img.style.left = (cx - (x0 + x1) / 2 * sc) + 'px';
  const tag = document.querySelector('.tag'); if (tag && !tag.dataset.fixed) tag.style.top = (H + drop - contentH + contentH * 0.30) + 'px';
}
document.fonts.ready.then(() => {
  document.querySelectorAll('[data-box]').forEach(fitBox);
  document.querySelectorAll('[data-col]').forEach(fitCol);
  fillBelow();
  document.body.dataset.ready = 1;
});
</script>
"""

_FACES = {}
for _line in (ASSETS / "faces.jsonl").read_text(encoding="utf-8").splitlines():
    _o = json.loads(_line)
    _FACES[_o["file"]] = _o


def uri(p) -> str:
    return Path(p).resolve().as_uri()


def esc(s: str) -> str:
    # «2026-yilda», «3-oy» не рвём на строке: word joiner вокруг дефиса после цифры
    s = re.sub(r"(\d)-(?=[A-Za-zА-Яа-я‘’])", "\\1\u2060-\u2060", s or "")
    # «AI-mutaxassis» не рвём на дефисе; цифру не оставляем одну в конце строки
    s = re.sub(r"\bAI-(?=\w)", "AI\u2060-\u2060", s)
    s = re.sub(r"(?<=\d) (?=[A-Za-zА-Яа-я‘’«])", "\u00a0", s)
    return html.escape(s, quote=True)


MONEY_RX = r"\$\s?\d[\d\s.,]*\d|\$\s?\d|\d[\d\s.,]*\s?\$|\d+(?:[.,]\d+)?\s?(?:mln|млн)\.?(?:\s?(?:so‘m|сум))?|\b0\s?(?:so‘m|сум)"


def mark(text: str, words=(), cls="kw", money=True) -> str:
    """Экранирует текст и оборачивает ключевые слова и суммы в <span class=cls>."""
    out = esc(text)
    pats = [re.escape(esc(w)) for w in words if w]
    if money:
        pats.append(MONEY_RX)
    if not pats:
        return out
    rx = re.compile("(" + "|".join(pats) + ")")
    return rx.sub(lambda m: f'<span class="{cls}">{m.group(0)}</span>', out)


def photo_bg(photo: Path, w: int, h: int, ty: float, tx: float = None, max_zoom: float = 1.35, face_index: int = 0) -> str:
    """CSS фона: фото cover, сдвиг/зум так, чтобы лицо было ближе к точке (tx, ty)."""
    im = ImageOps.exif_transpose(Image.open(photo))
    iw, ih = im.size
    meta = _FACES.get(photo.name)
    faces = meta["faces"] if meta else []
    fx, fy = (faces[face_index][0], faces[face_index][1]) if faces else (0.5, 0.4)
    tx = w / 2 if tx is None else tx
    s0 = max(w / iw, h / ih)
    best = None
    z = 1.0
    while z <= max_zoom + 1e-6:
        s = s0 * z
        sw, sh = iw * s, ih * s
        oy = min(0, max(h - sh, ty - fy * sh))
        ox = min(0, max(w - sw, tx - fx * sw))
        err = abs(fy * sh + oy - ty) + 0.5 * abs(fx * sw + ox - tx) + 260 * (z - 1)
        if best is None or err < best[0]:
            best = (err, sw, sh, ox, oy)
        z += 0.05
    _, sw, sh, ox, oy = best
    return f"background-image:url({uri(photo)});background-size:{sw:.0f}px {sh:.0f}px;background-position:{ox:.0f}px {oy:.0f}px;background-repeat:no-repeat"


def page(w: int, h: int, css: str, body: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<link rel='stylesheet' href='{FONTS}'>"
        "<style>html,body{margin:0;padding:0}"
        f"body{{width:{w}px;height:{h}px;position:relative;overflow:hidden;"
        "-webkit-font-smoothing:antialiased;text-rendering:geometricPrecision}"
        "*{box-sizing:border-box}"
        ".hl{display:inline;-webkit-box-decoration-break:clone;box-decoration-break:clone}"
        ".strike{position:relative;white-space:nowrap;display:inline-block}"
        ".strike:after{content:'';position:absolute;left:-5%;right:-5%;top:50%;height:.1em;background:#ff2a2a;transform:rotate(-7deg);border-radius:.05em}"
        ".nb{white-space:nowrap}"
        ".abs{position:absolute}"
        + css
        + "</style></head><body>"
        + body
        + FIT_JS
        + "</body></html>"
    )


# ---------------------------------------------------------------- 1.2 Вопрос-ответ

QA_THEMES = {
    "insta": {"head_bg": "linear-gradient(90deg,#8E2BD9 0%,#D2337A 55%,#F5333F 100%)", "head_fg": "#fff", "q_grad": "linear-gradient(90deg,#8E1EB0,#D61F69)"},
    "pink": {"head_bg": "#F8CBD8", "head_fg": "#3a3a3a", "q_color": "#222"},
    "black": {"head_bg": "#1C1C1C", "head_fg": "#fff", "q_color": "#2a2a2a"},
    "orange": {"head_bg": "linear-gradient(90deg,#F7902F,#F2622B)", "head_fg": "#fff", "q_grad": "linear-gradient(90deg,#F08A2E,#E6602A)"},
}

QA_CSS = """
.bg{position:absolute;inset:0}
.shade{position:absolute;inset:0}
.col{position:absolute;display:flex;flex-direction:column;align-items:center;justify-content:space-between}
.ans{display:flex;flex-direction:column;align-items:center;gap:.5em;width:100%}
.sticker{width:17.6em;border-radius:.74em;overflow:hidden;background:#fff;box-shadow:0 .25em .7em rgba(0,0,0,.22);flex:none}
.sh{height:2.05em;display:flex;align-items:center;justify-content:center;font:500 .72em/1 Inter,sans-serif;letter-spacing:.01em}
.sq{padding:.62em .9em .78em;text-align:center;font:500 1em/1.24 Inter,sans-serif}
.g{-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:transparent}
.blk{max-width:21em;text-align:center}
.blk.r{text-align:right;align-self:flex-end}
.blk.l{text-align:left;align-self:flex-start}
.strong{font:500 1.34em/1.13 'Roboto Condensed',sans-serif;text-transform:uppercase}
.classic{font:700 1.12em/1.3 Inter,sans-serif}
.serif{font:400 1.12em/1.3 'PT Serif',serif}
.tw{font:700 1em/1.36 'Courier Prime',monospace}
.modern{font:italic 600 .92em/1.42 Montserrat,sans-serif;text-transform:uppercase;letter-spacing:.14em}
.hl{padding:.08em .32em;border-radius:.26em}
.tw .hl{border-radius:.08em;padding:.04em .2em}
.modern .hl{border-radius:.12em;padding:.1em .34em}
.price{display:flex;gap:.45em;align-items:center;justify-content:center;flex-wrap:wrap}
.price .old{font:700 1.05em/1 Inter,sans-serif;background:#fff;color:#333;padding:.22em .4em;border-radius:.24em}
.price .new{font:800 1.5em/1 Inter,sans-serif;padding:.16em .4em;border-radius:.24em}
"""


def qa_blocks(f: dict, recipe: dict) -> str:
    parts = []
    for i, text in enumerate(f.get("answer", [])):
        st = recipe["answer"][min(i, len(recipe["answer"]) - 1)]
        parts.append(
            f'<div class="blk {st.get("align","")} {st["font"]}"><span class="hl" style="background:{st["bg"]};color:{st["fg"]}">'
            f'{mark(text, recipe.get("kw", []))}</span></div>'
        )
    if f.get("bullets"):
        st = recipe["bullets"]
        inner = "<br>".join(f'<span class="hl" style="background:{st["bg"]};color:{st["fg"]}">— {esc(b)}</span>' for b in f["bullets"])
        parts.append(f'<div class="blk {st.get("align","r")} {st["font"]}">{inner}</div>')
    if f.get("price_new"):
        st = recipe["price"]
        parts.append(
            f'<div class="price"><span class="old"><span class="strike">{esc(f.get("price_old",""))}</span></span>'
            f'<span class="new" style="background:{st["bg"]};color:{st["fg"]}">{esc(f["price_new"])}</span></div>'
        )
    if f.get("cta"):
        st = recipe["cta"]
        parts.append(f'<div class="blk {st["font"]}"><span class="hl" style="background:{st["bg"]};color:{st["fg"]}">{esc(f["cta"])}&nbsp;⬇️</span></div>')
    return "".join(parts)


def build_qa(c: dict, f: dict, fmt: str, st: dict) -> str:
    w, h = FORMATS[fmt]
    th = QA_THEMES[st["theme"]]
    if "q_grad" in th:
        q_html = f'<span class="g" style="background-image:{th["q_grad"]}">{esc(f["question"])}</span>'
    else:
        q_html = f'<span style="color:{th["q_color"]}">{esc(f["question"])}</span>'
    if fmt == "story":
        box, face_y = f"left:64px;right:64px;top:250px;bottom:330px;font-size:{st.get('fs_story', 46)}px", st.get("face_y_story", 800)
    else:
        box, face_y = f"left:56px;right:56px;top:52px;bottom:52px;font-size:{st.get('fs_feed', 40)}px", st.get("face_y_feed", 470)
    kwcss = f'.kw{{color:{st["recipe"].get("kw_color","inherit")}}}'
    body = (
        f'<div class="bg" style="{photo_bg(st["photo"], w, h, face_y, max_zoom=st.get("zoom", 1.3))}"></div>'
        f'<div class="shade" style="background:{st.get("shade","none")}"></div>'
        f'<div class="col" data-col style="{box}">'
        f'<div class="sticker" style="transform:rotate({st.get("rot",0)}deg)">'
        f'<div class="sh" style="background:{th["head_bg"]};color:{th["head_fg"]}">{esc(f.get("sticker_title",""))}</div>'
        f'<div class="sq">{q_html}</div></div>'
        f'<div class="ans">{qa_blocks(f, st["recipe"])}</div>'
        "</div>"
    )
    return page(w, h, QA_CSS + kwcss, body)


# ---------------------------------------------------------------- 1.1 Эксперт на картинке

EX_CSS = """
.exbg{position:absolute;inset:0;background:radial-gradient(120% 80% at 50% 35%,#FFFFFF 0%,#F1F1F1 60%,#E6E6E6 100%)}
.band{position:absolute;transform-origin:center}
.headwrap{position:absolute;text-align:center}
.head{font:800 1em/1.1 Montserrat,sans-serif;color:#262626;letter-spacing:-.005em}
.head .kw{color:#EE3330}
.sub{font:700 .62em/1.25 Montserrat,sans-serif;color:#262626;margin-top:.45em}
.sub .kw{color:#EE3330}
.pill{display:inline-block;margin-top:.55em;background:#EE3330;color:#fff;font:600 .56em/1.2 Montserrat,sans-serif;padding:.55em 1.35em;border-radius:999px;box-shadow:0 .3em .7em rgba(238,51,48,.35)}
.cut{position:absolute;filter:drop-shadow(0 0 14px #fff) drop-shadow(0 0 5px #fff);-webkit-mask-image:linear-gradient(to bottom,#000 78%,transparent 99%);mask-image:linear-gradient(to bottom,#000 78%,transparent 99%)}
.cut.side{-webkit-mask-image:linear-gradient(to bottom,#000 78%,transparent 99%),linear-gradient(to right,transparent 0,#000 9%,#000 91%,transparent 100%);-webkit-mask-composite:source-in;mask-image:linear-gradient(to bottom,#000 78%,transparent 99%),linear-gradient(to right,transparent 0,#000 9%,#000 91%,transparent 100%);mask-composite:intersect}
.tag{position:absolute;background:#fff;border:2px solid #2b2b2b;border-radius:12px;padding:14px 26px 14px 30px;font:500 32px/1.15 Inter,sans-serif;color:#222;box-shadow:0 6px 18px rgba(0,0,0,.08)}
.tag small{display:block;font:400 24px/1.2 Inter,sans-serif;color:#666}
.tag:before{content:'';position:absolute;left:-13px;top:-13px;width:26px;height:26px;border-radius:50%;background:#EE3330}
.ph{position:absolute;border-radius:28px;overflow:hidden;box-shadow:0 18px 40px rgba(0,0,0,.25);background:#fff}
.ph .bar{height:46px;background:#EDEDED;display:flex;align-items:center;gap:10px;padding:0 18px}
.ph .bar i{width:14px;height:14px;border-radius:50%;background:#ccc;display:block}
.ph .shot{position:absolute;left:0;right:0;top:46px;bottom:0;background:repeating-linear-gradient(45deg,#f4f4f4 0 22px,#ececec 22px 44px);display:flex;align-items:center;justify-content:center;font:700 34px/1.2 Inter;color:#9a9a9a;text-align:center}
.notif{position:absolute;background:rgba(255,255,255,.96);border-radius:30px;box-shadow:0 14px 34px rgba(0,0,0,.22);display:flex;gap:20px;align-items:center;padding:22px 26px;font:500 30px/1.25 Inter,sans-serif;color:#111}
.notif .ic{width:72px;height:72px;border-radius:18px;background:linear-gradient(135deg,#7B2FF7,#A346FF);flex:none;display:flex;align-items:center;justify-content:center;color:#fff;font:800 38px Inter}
.notif b{display:block;font-weight:700}
.pay{position:absolute;display:block;border-radius:30px;box-shadow:0 18px 44px rgba(0,0,0,.38);transform:rotate(3deg)}
"""


def bands(fmt: str) -> str:
    if fmt == "story":
        return (
            '<div class="band" style="width:1100px;height:300px;right:-430px;top:-60px;transform:rotate(36deg);background:rgba(160,160,160,.28)"></div>'
            '<div class="band" style="width:1000px;height:130px;right:-430px;top:40px;transform:rotate(36deg);background:#EE3330"></div>'
            '<div class="band" style="width:1100px;height:300px;left:-520px;bottom:300px;transform:rotate(36deg);background:rgba(160,160,160,.28)"></div>'
            '<div class="band" style="width:1000px;height:140px;left:-560px;bottom:180px;transform:rotate(36deg);background:#EE3330"></div>'
        )
    return (
        '<div class="band" style="width:900px;height:240px;right:-380px;top:-70px;transform:rotate(36deg);background:rgba(160,160,160,.28)"></div>'
        '<div class="band" style="width:820px;height:110px;right:-380px;top:10px;transform:rotate(36deg);background:#EE3330"></div>'
        '<div class="band" style="width:900px;height:240px;left:-480px;bottom:40px;transform:rotate(36deg);background:rgba(160,160,160,.28)"></div>'
        '<div class="band" style="width:820px;height:120px;left:-500px;bottom:-30px;transform:rotate(36deg);background:#EE3330"></div>'
    )


def build_expert(c: dict, f: dict, fmt: str, st: dict) -> str:
    w, h = FORMATS[fmt]
    kw = st.get("kw", [])
    head = f'<div class="head">{mark(f["headline"], kw)}</div>'
    sub = ""
    if f.get("subline"):
        sub += f'<div class="sub">{mark(f["subline"], kw)}</div>'
    if f.get("course_name"):
        sub += f'<div class="sub" style="color:#EE3330">{esc(f["course_name"])}</div>'
    cta = f'<div class="pill">{esc(f["cta"])}</div>' if f.get("cta") else ""
    cut = CUT / st["cutout"]
    cim = Image.open(cut)
    bb = cim.getbbox()
    cw, ch = bb[2] - bb[0], bb[3] - bb[1]
    tag = f'<div class="tag"{" data-fixed=1" if st.get("tag_fixed") else ""} style="{{pos}}">{esc(st.get("name","Nikita"))}<small>{esc(st.get("role",""))}</small></div>'
    extra = ""
    if fmt == "story":
        hh = st.get("cut_h_story", 1080)
        scale = hh / ch
        img_w = cim.width * scale
        cx = st.get("cut_cx_story", w / 2)
        left = cx - (bb[0] + cw / 2) * scale
        top = h - hh - bb[1] * scale + st.get("cut_drop_story", 40)
        fill = f'data-fill="{bb[0]},{bb[1]},{bb[2]},{bb[3]},{cim.width},{cim.height},{cx:.0f},{st.get("cut_drop_story", 40)},{st.get("cut_max_story", 1400)}"'
        cut_html = f'<img class="cut{" side" if st.get("side_fade") else ""}" {fill} src="{uri(cut)}" style="width:{img_w:.0f}px;left:{left:.0f}px;top:{top:.0f}px">'
        text = f'<div class="headwrap" data-box data-maxh="{st.get("head_maxh_story", 640)}" style="left:70px;right:70px;top:250px;font-size:{st.get("head_fs_story", 78)}px">{head}{sub}{cta}</div>'
        tagpos = st.get("tag_story", "left:60px;top:1240px")
        if c["id"] in ("I1-3", "I1-3B"):
            extra = mockup_site(f, "story")
    else:
        hh = st.get("cut_h_feed", 900)
        scale = hh / ch
        img_w = cim.width * scale
        left = st.get("cut_x_feed", w - cw * scale + 30) - bb[0] * scale
        top = h - hh - bb[1] * scale + st.get("cut_drop_feed", 30)
        cut_html = f'<img class="cut{" side" if st.get("side_fade") else ""}" src="{uri(cut)}" style="width:{img_w:.0f}px;left:{left:.0f}px;top:{top:.0f}px">'
        text = f'<div class="headwrap" data-box data-maxh="{st.get("head_maxh_feed", 760)}" style="left:60px;width:{st.get("text_w_feed", 600)}px;top:70px;text-align:left;font-size:{st.get("head_fs_feed", 64)}px">{head}{sub}{cta}</div>'
        tagpos = st.get("tag_feed", "left:60px;top:1020px")
        if c["id"] in ("I1-3", "I1-3B"):
            extra = mockup_site(f, "feed")
    body = '<div class="exbg"></div>' + bands(fmt) + extra + cut_html + text + tag.replace("{pos}", tagpos)
    return page(w, h, EX_CSS, body)


def mockup_site(f: dict, fmt: str) -> str:
    """Окно браузера со скриншотом сайта (assets/site_screenshot.png). Если в креативе есть поле payment — рядом настоящий скрин поступления."""
    shot = ASSETS / "site_screenshot.png"
    inner = f'<img src="{uri(shot)}" style="width:100%;display:block">' if shot.exists() else "SAYT SKRINSHOTI<br>(Vasya yuboradi)"
    pay = ASSETS / f["payment"] if f.get("payment") else None
    story = fmt == "story"
    win = (
        f'<div class="ph" style="left:70px;top:820px;width:560px;height:620px;transform:rotate(-4deg)">' if story
        else f'<div class="ph" style="left:60px;top:560px;width:470px;height:500px;transform:rotate(-4deg)">'
    ) + f'<div class="bar"><i></i><i></i><i></i></div><div class="shot">{inner}</div></div>'
    if not pay:
        return win
    pos = "left:70px;top:1110px;width:400px" if story else "left:50px;top:950px;width:360px"
    return win + f'<img class="pay" src="{uri(pay)}" style="{pos}">'


# ---------------------------------------------------------------- 1.3 Текст и фон

TX_CSS = """
.bg{position:absolute;inset:0}
.shade{position:absolute;inset:0}
.stack{position:absolute;display:flex;flex-direction:column;align-items:center;gap:.18em}
.b1{font:900 1em/1.02 Montserrat,sans-serif;text-transform:uppercase;padding:.14em .32em;text-align:center}
.b2{font:800 .44em/1.15 Montserrat,sans-serif;text-transform:uppercase;padding:.3em .6em;text-align:center}
.strip{position:absolute;left:0;right:0;text-align:center}
.strip span{display:inline-block;font:800 34px/1.2 Montserrat,sans-serif;text-transform:uppercase;padding:14px 26px}
.q{font:800 1em/1.18 Montserrat,sans-serif}
.q .hl{background:#FFC21A;color:#111;padding:.06em .3em;border-radius:.16em}
.it{font:italic 800 1em/1.2 Montserrat,sans-serif;color:#fff;text-align:right;text-shadow:0 2px 10px rgba(0,0,0,.35)}
.it .kw{background:#FFC21A;color:#111;padding:0 .2em;border-radius:.12em;text-shadow:none}
.mini{display:inline-block;font:800 32px/1.2 Montserrat,sans-serif;text-transform:uppercase;background:#FFD95A;color:#111;padding:10px 22px}
"""


def build_text(c: dict, f: dict, fmt: str, st: dict) -> str:
    w, h = FORMATS[fmt]
    story = fmt == "story"
    face_y = st.get("face_y_story" if story else "face_y_feed", 1000 if story else 700)
    bg = f'<div class="bg" style="{photo_bg(st["photo"], w, h, face_y, max_zoom=st.get("zoom", 1.3))}"></div><div class="shade" style="background:{st.get("shade","none")}"></div>'
    if st["layout"] == "blocks":  # «ВЫ МАМА? ЛЮБИТЕ ПЕЧЬ?»
        top = 300 if story else 90
        fs = st.get("blocks_fs_story", 84) if story else st.get("blocks_fs_feed", 74)
        lines = st.get("split") or [f["headline"]]
        b1 = "".join(
            f'<div class="b1" style="background:{"#FFC21A" if i % 2 == 0 else "#111"};color:{"#111" if i % 2 == 0 else "#fff"}">{mark(t, money=False)}</div>'
            for i, t in enumerate(lines)
        )
        sub = f'<div class="b2" style="background:#FFC21A;color:#111;margin-top:.3em">{esc(f.get("subline",""))}</div>' if f.get("subline") else ""
        stack = f'<div class="stack" data-box data-maxh="{820 if story else 640}" style="left:60px;right:60px;top:{top}px;font-size:{fs}px">{b1}{sub}</div>'
        bul = " · ".join(esc(b) for b in f.get("bullets", []))
        bottom = 330 if story else 50
        strips = (
            f'<div class="abs" style="left:40px;right:40px;bottom:{bottom}px;display:flex;flex-direction:column;align-items:center;gap:14px;text-align:center">'
            + (f'<span class="hl" style="background:#111;color:#fff;font:800 32px/1.5 Montserrat,sans-serif;text-transform:uppercase;padding:6px 18px">{bul}</span>' if bul else "")
            + f'<span style="display:inline-block;background:#FFC21A;color:#111;font:800 36px/1.2 Montserrat,sans-serif;text-transform:uppercase;padding:14px 26px">{esc(f.get("cta",""))}&nbsp;⬇️</span></div>'
        )
        return page(w, h, TX_CSS, bg + stack + strips)
    # layout "dark" — «Занимаетесь спортом?»
    q = f'<div class="q abs" data-box data-maxh="{520 if story else 420}" style="left:70px;right:150px;top:{280 if story else 80}px;font-size:{st.get("q_fs_story", 68) if story else st.get("q_fs_feed", 58)}px"><span class="hl">{esc(f["headline"])}</span></div>'
    rocket = f'<div class="abs" style="right:60px;top:{300 if story else 90}px;font-size:{110 if story else 90}px;transform:rotate(12deg)">🚀</div>'
    path_top = 860 if story else 560
    plane = (
        f'<svg class="abs" style="left:0;top:{path_top - 120}px" width="1080" height="420" viewBox="0 0 1080 420">'
        '<path d="M120 60 C 420 20, 520 180, 760 150 S 980 260, 900 400" fill="none" stroke="#FFD95A" stroke-width="7" stroke-dasharray="22 18" stroke-linecap="round"/></svg>'
        f'<div class="abs" style="left:520px;top:{path_top - 70}px;font-size:84px;transform:rotate(-18deg)">✈️</div>'
    )
    it = f'<div class="it abs" data-box data-maxh="{330 if story else 260}" style="right:64px;left:120px;top:{1080 if story else 760}px;font-size:{st.get("it_fs_story", 60) if story else st.get("it_fs_feed", 50)}px">{mark(f.get("subline",""), st.get("kw", []))}</div>'
    cta_y = 1470 if story else 1110
    cta = f'<div class="abs" style="right:64px;top:{cta_y}px;text-align:right"><span class="mini">{esc(f.get("cta",""))}&nbsp;⬇️</span></div>'
    scrib = f'<svg class="abs" style="right:90px;top:{cta_y + 70}px" width="300" height="90" viewBox="0 0 300 90"><path d="M10 60 C 60 10, 80 80, 120 40 S 190 10, 210 55 S 270 80, 290 20" fill="none" stroke="#FFD95A" stroke-width="7" stroke-linecap="round"/></svg>'
    return page(w, h, TX_CSS, bg + q + rocket + plane + it + cta + scrib)


# ---------------------------------------------------------------- мемы

MEME_CSS = """
.c{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
.logo{display:flex;align-items:center;gap:.08em;font:800 1em/1 Montserrat,sans-serif;letter-spacing:-.01em}
.logo .w{color:#fff}
.logo .o{background:#FF9000;color:#000;border-radius:.12em;padding:.05em .14em .1em}
.ln{font:500 1em/1.3 Montserrat,sans-serif;color:#fff}
"""


def build_m1(c, f, fmt, st):
    w, h = FORMATS[fmt]
    story = fmt == "story"
    logo = f'<div class="logo" data-box data-maxw="940" style="font-size:{170 if story else 160}px"><span class="w">{esc(f["logo_word_white"])}</span><span class="o">{esc(f["logo_word_box"])}</span></div>'
    lines = (
        f'<div class="ln" data-box data-maxh="{420 if story else 330}" style="font-size:{58 if story else 52}px;margin-top:70px;max-width:900px">{esc(f["line1"])}<br>{esc(f["line2"])}</div>'
        f'<div style="margin-top:{90 if story else 60}px;font:700 {50 if story else 44}px/1.2 Montserrat,sans-serif;color:#000;background:#FF9000;border-radius:14px;padding:18px 40px">{esc(f["cta"])}</div>'
    )
    return page(w, h, MEME_CSS + "body{background:#000}", f'<div class="c">{logo}{lines}</div>')


def build_m3(c, f, fmt, st):
    w, h = FORMATS[fmt]
    story = fmt == "story"
    bg = f'<div class="abs" style="inset:0;{photo_bg(st["photo"], w, h, 820 if story else 560, tx=330)};filter:brightness(.5) saturate(.75)"></div>'
    lab = (
        f'<div class="abs" data-box data-maxw="1000" style="left:40px;top:{250 if story else 70}px;font-size:{80 if story else 70}px">'
        f'<div style="display:inline-block;background:#fff;color:#111;font:800 1em/1.1 Montserrat,sans-serif;padding:.12em .3em;transform:rotate(-3deg)">{esc(f["title_line1"])}</div><br>'
        f'<div style="display:inline-block;margin:.1em 0 0 1.4em;background:#fff;color:#111;font:800 1em/1.1 Montserrat,sans-serif;padding:.12em .3em;transform:rotate(-3deg)">{esc(f["title_line2"])}</div></div>'
    )
    sub = f'<div class="abs" data-box data-maxh="{300 if story else 230}" style="left:70px;width:{640 if story else 600}px;top:{560 if story else 330}px;font:800 {58 if story else 48}px/1.18 Montserrat,sans-serif;color:#fff;text-shadow:0 2px 12px rgba(0,0,0,.4)">{esc(f["subline"])}</div>'
    py = 960 if story else 640
    price = (
        f'<div class="abs" style="right:70px;top:{py}px;text-align:right;color:#fff;text-shadow:0 3px 18px rgba(0,0,0,.55)">'
        f'<div style="font:300 {92 if story else 76}px/1.02 Roboto,sans-serif">{esc(f["today"])}</div>'
        f'<div style="font:300 {86 if story else 70}px/1.1 Roboto,sans-serif"><span class="strike">{esc(f["price_old"])}</span></div>'
        f'<div style="font:900 {104 if story else 86}px/1 Roboto,sans-serif;color:#FF2A2A">{esc(f["price_new"])}</div></div>'
    )
    cats = (
        f'<img class="abs" src="{uri(CUT / "cat_left.png")}" style="left:-30px;bottom:{-10 if story else -20}px;width:{560 if story else 470}px">'
        f'<img class="abs" src="{uri(CUT / "cat_right.png")}" style="right:-20px;bottom:{-10 if story else -20}px;width:{500 if story else 420}px">'
    )
    return page(w, h, "", bg + lab + sub + price + cats)


def build_m4(c, f, fmt, st):
    w, h = FORMATS[fmt]
    img = ASSETS / "memes" / "M4_clean.jpg"
    iw, ih = Image.open(img).size
    s = max(w / iw, h / ih)
    sw, sh = iw * s, ih * s
    ox, oy = (w - sw) / 2, (h - sh) / 2
    px0, py0, px1, py1 = st["paper"]
    L, T, R, B = ox + px0 * s, oy + py0 * s, ox + px1 * s, oy + py1 * s
    txt = (
        f'<div class="abs" style="left:{L:.0f}px;top:{T:.0f}px;width:{R - L:.0f}px;height:{B - T:.0f}px;display:flex;align-items:center;justify-content:center;transform:rotate(-.6deg)">'
        f'<div data-box data-maxh="{(B - T) * 0.94:.0f}" style="display:flex;flex-direction:column;align-items:center;gap:1.1em;text-align:center;color:#1d1d1d;font-size:{st["fs"] * s:.0f}px;opacity:.93;mix-blend-mode:multiply">'
        f'<div style="font:500 1em/1.25 Montserrat,sans-serif">{esc(f["line1"])}</div>'
        f'<div style="font:600 1.12em/1.2 Montserrat,sans-serif">{esc(f["line2"])}</div>'
        f'<div style="font:500 .78em/1.25 Montserrat,sans-serif;color:#333">{esc(f["line3"])}</div></div></div>'
    )
    bg = f'<div class="abs" style="inset:0;background:url({uri(img)}) {ox:.0f}px {oy:.0f}px/{sw:.0f}px {sh:.0f}px no-repeat"></div>'
    return page(w, h, "", bg + txt)


def build_m5(c, f, fmt, st):
    w, h = FORMATS[fmt]
    story = fmt == "story"
    body = (
        f'<div class="c" style="padding:0 70px">'
        f'<div data-box data-maxh="{600 if story else 470}" style="font:900 {104 if story else 92}px/1.06 Montserrat,sans-serif;color:#111;max-width:940px">{esc(f["headline"])}</div>'
        f'<div style="margin-top:{80 if story else 50}px;font:700 {84 if story else 72}px/1 Montserrat,sans-serif;color:#9a9a9a"><span class="strike">{esc(f["price_old"])}</span></div>'
        f'<div data-box data-maxw="940" style="margin-top:{36 if story else 26}px;font:900 {170 if story else 140}px/1 Montserrat,sans-serif;color:#E5197F;letter-spacing:-.02em;white-space:nowrap">{esc(f["free"])}</div>'
        f'<div style="margin-top:{80 if story else 50}px;font:800 {60 if story else 52}px/1 Montserrat,sans-serif;color:#fff;background:#111;border-radius:999px;padding:26px 70px">{esc(f["cta"])} 👇</div>'
        "</div>"
    )
    return page(w, h, MEME_CSS + "body{background:#fff}", body)


def build_m6(c, f, fmt, st):
    w, h = FORMATS[fmt]
    story = fmt == "story"
    p1, p2 = ASSETS / "memes" / "M6_p1.jpg", ASSETS / "memes" / "M6_p2.jpg"
    font = "Montserrat Alternates"
    sc = 0.86 if story else 0.8
    pw, ph = 1080 * sc, 556 * sc
    lx = (1080 - pw) / 2
    top_y, top_h = (240, 230) if story else (26, 200)
    top = f'<div class="abs" data-box data-maxh="{top_h}" style="left:50px;right:50px;top:{top_y}px;height:{top_h}px;display:flex;align-items:center;justify-content:center;text-align:center;font:800 {70 if story else 60}px/1.12 \'{font}\',sans-serif;color:#111">{esc(f["top"])}</div>'
    y1 = top_y + top_h + 14
    panels = (
        f'<img class="abs" src="{uri(p1)}" style="left:{lx:.0f}px;top:{y1:.0f}px;width:{pw:.0f}px;height:{ph:.0f}px;outline:3px solid #222">'
        f'<img class="abs" src="{uri(p2)}" style="left:{lx:.0f}px;top:{y1 + ph + 3:.0f}px;width:{pw:.0f}px;height:{ph:.0f}px;outline:3px solid #222">'
    )
    hx, hy, hw, hh = st["hole"]
    holetxt = f'<div class="abs" data-box data-maxh="{hh * sc:.0f}" data-maxw="{hw * sc:.0f}" style="left:{lx + hx * sc:.0f}px;top:{y1 + ph + 3 + hy * sc:.0f}px;width:{hw * sc:.0f}px;display:flex;align-items:center;justify-content:center;text-align:center;font:700 {66 * sc:.0f}px/1.15 \'{font}\',sans-serif;color:#111;min-height:{hh * sc:.0f}px">{esc(f["in_meme"])}</div>'
    by = y1 + 2 * ph + 30
    bottom = f'<div class="abs" data-box data-maxh="{h - by - (300 if story else 24):.0f}" style="left:50px;right:50px;top:{by:.0f}px;text-align:center;font:800 {70 if story else 58}px/1.12 \'{font}\',sans-serif;color:#8E5BD0">{esc(f["bottom"])}</div>'
    return page(w, h, "body{background:#fff}", top + panels + holetxt + bottom)


def build_m7(c, f, fmt, st):
    w, h = FORMATS[fmt]
    story = fmt == "story"
    al, ar = ASSETS / "memes" / "M7_aliens_left.png", ASSETS / "memes" / "M7_aliens_right.png"
    aw = 760 if story else 600
    body = (
        f'<div class="c" style="padding:0 60px;gap:{34 if story else 22}px">'
        f'<img src="{uri(al)}" style="width:{aw}px">'
        f'<div data-box data-maxh="{330 if story else 250}" style="font:700 {80 if story else 68}px/1.1 Roboto,sans-serif;color:#fff;max-width:960px">{esc(f["headline"])}</div>'
        f'<div style="font:900 {74 if story else 62}px/1 Montserrat,sans-serif;color:#fff"><span class="strike">{esc(f["price_old"])}</span></div>'
        f'<div style="font:900 {130 if story else 108}px/1 Montserrat,sans-serif;color:#D63CF0">{esc(f["free"])}</div>'
        f'<div data-box data-maxh="{200 if story else 150}" style="font:800 {50 if story else 42}px/1.2 Montserrat,sans-serif;color:#fff;max-width:900px;text-wrap:balance">{esc(f["cta"])}</div>'
        f'<img src="{uri(ar)}" style="width:{aw}px">'
        "</div>"
    )
    return page(w, h, MEME_CSS + "body{background:#191919}", body)


# ---------------------------------------------------------------- 2. Красивые дизайны (карусели 1:1)

K_CSS = """
body{background:#F5F1EA;color:#121212}
.kbg{position:absolute;inset:0;background:radial-gradient(70% 60% at 85% 10%,rgba(91,60,255,.10),transparent 60%),radial-gradient(60% 50% at 0% 100%,rgba(33,230,193,.12),transparent 60%),#F5F1EA}
.badge{position:absolute;left:70px;top:64px;background:#121212;color:#F5F1EA;font:700 28px/1 Inter,sans-serif;padding:16px 26px;border-radius:999px;letter-spacing:.02em}
.num{position:absolute;right:50px;top:30px;font:900 190px/1 Montserrat,sans-serif;color:transparent;-webkit-text-stroke:3px rgba(18,18,18,.16)}
.ttl{position:absolute;left:70px;right:70px;font:800 66px/1.06 Montserrat,sans-serif;letter-spacing:-.01em}
.rows{position:absolute;left:70px;right:70px;display:flex;flex-direction:column}
.row{padding:22px 0;border-top:2px solid rgba(18,18,18,.12)}
.row .lb{font:700 28px/1.2 Inter,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:#6B6660;margin-bottom:8px}
.row .vl{font:600 42px/1.22 Inter,sans-serif}
.hi{background:#5B3CFF;color:#fff}
.hi .kbg{background:radial-gradient(70% 60% at 85% 10%,rgba(255,255,255,.18),transparent 60%),#5B3CFF}
.hi .row{border-top-color:rgba(255,255,255,.25)} .hi .row .lb{color:rgba(255,255,255,.7)} .hi .num{-webkit-text-stroke-color:rgba(255,255,255,.3)} .hi .badge{background:#fff;color:#5B3CFF}
.small{position:absolute;left:70px;right:70px;bottom:120px;font:500 30px/1.3 Inter,sans-serif;opacity:.75}
.dots{position:absolute;left:70px;bottom:60px;display:flex;gap:12px}
.dots i{width:16px;height:16px;border-radius:50%;background:rgba(18,18,18,.18)}
.dots i.on{background:#5B3CFF;width:44px;border-radius:9px}
.hi .dots i{background:rgba(255,255,255,.35)} .hi .dots i.on{background:#fff}
.hook{position:absolute;left:70px;width:640px;font:900 92px/1.02 Montserrat,sans-serif;letter-spacing:-.02em}
.sub{position:absolute;left:70px;width:600px;font:500 38px/1.3 Inter,sans-serif;color:#3a3633}
.btn{display:inline-block;background:#5B3CFF;color:#fff;font:800 40px/1.1 Montserrat,sans-serif;padding:30px 50px;border-radius:999px;box-shadow:0 16px 40px rgba(91,60,255,.35)}
.swipe{position:absolute;right:70px;bottom:52px;font:700 28px/1 Inter,sans-serif;color:#6B6660}
.kcut{position:absolute;filter:drop-shadow(0 30px 40px rgba(0,0,0,.18))}
.avatar{position:absolute;right:70px;top:64px;width:230px;height:230px;border-radius:50%;overflow:hidden;background:#E3DCFF;box-shadow:0 18px 40px rgba(0,0,0,.22)}
.avatar img{width:100%;height:100%;object-fit:cover;object-position:30% 6%}
.hi .avatar{background:#fff}
"""


def k_rows(text: str) -> str:
    parts = [x.strip() for x in text.split("·") if x.strip()]
    out = []
    for part in parts:
        if ":" in part:
            lb, vl = part.split(":", 1)
            out.append(f'<div class="row"><div class="lb">{esc(lb.strip())}</div><div class="vl">{mark(vl.strip())}</div></div>')
        else:
            out.append(f'<div class="row"><div class="vl">{mark(part)}</div></div>')
    return "".join(out)


def build_k_card(t: dict, card: dict, idx: int, total: int, lang: str) -> str:
    w = h = 1080
    dots = '<div class="dots">' + "".join(f'<i class="{"on" if i == idx else ""}"></i>' for i in range(total)) + "</div>"
    is_first, is_last = idx == 0, idx == total - 1
    title = card.get("title", "")
    text = card.get("text", "")
    if is_first:
        cut = CUT / t.get("cutout", "nikita_04.png")
        body = (
            '<div class="kbg"></div>'
            f'<div class="badge">{esc(t.get("badge",""))}</div>'
            f'<div class="hook" data-box data-maxh="520" style="top:170px;width:600px">{esc(title)}</div>'
            f'<div class="sub" data-box data-maxh="250" style="top:720px;width:520px">{esc(text)}</div>'
            f'<img class="kcut" src="{uri(cut)}" style="right:-50px;bottom:0;height:{t.get("cut_h", 760)}px">'
            + dots + f'<div class="swipe">→</div>'
        )
        return page(w, h, K_CSS, body)
    if is_last:
        cut = CUT / t.get("cutout_last", "nikita_03.png")
        body = (
            '<div class="kbg"></div>'
            f'<div class="hook" data-box data-maxh="430" style="top:110px;width:700px;font-size:76px">{esc(title)}</div>'
            f'<div class="sub" data-box data-maxh="220" style="top:560px;width:600px">{esc(text)}</div>'
            f'<div class="abs" style="left:70px;top:800px"><span class="btn">{esc(card.get("cta") or t.get("cta",""))} →</span></div>'
            f'<img class="kcut" src="{uri(cut)}" style="right:-30px;bottom:0;height:700px">'
            + dots
        )
        return page(w, h, K_CSS, body)
    hi = card.get("highlight", False)
    av = K_AVATARS.get(idx)
    face = f'<div class="avatar"><img src="{uri(CUT / av)}"></div>' if av else ""
    body = (
        '<div class="kbg"></div>'
        + (face if av else f'<div class="num">{idx:02d}</div>')
        +
        f'<div class="ttl" data-box data-maxh="230" style="top:{90}px;right:330px">{esc(title)}</div>'
        f'<div class="rows" data-box data-maxh="640" style="top:330px">{k_rows(text)}</div>'
        + (f'<div class="small">{esc(card["small"])}</div>' if card.get("small") else "")
        + dots
    )
    return page(w, h, K_CSS + (".hi-wrap{}" if hi else ""), f'<div class="{"hi" if hi else ""}" style="position:absolute;inset:0">{body}</div>')


# ---------------------------------------------------------------- стили по креативам

P = {
    "01": ASSETS / "photos" / "n01.jpg",
    "03": PHOTOS / "2026-10-11 00.39.06.jpg",
    "04": PHOTOS / "2026-10-11 00.39.24.jpg",
    "05": PHOTOS / "2026-10-11 00.39.56.jpg",
    "17": PHOTOS / "Story Aug 3, 2024 at 00:17.jpeg",
    "21": PHOTOS / "Story Oct 5, 2026 at 01:02.jpeg",
}
_FACES[P["01"].name] = {"faces": [[0.515, 0.42, 0.29, 0.34]]}

STYLE = {
    "I1-1": {"cutout": "nikita_17.png", "cut_h_story": 1240, "cut_cx_story": 600, "side_fade": True, "cut_h_feed": 880, "cut_x_feed": 560, "name": "Nikita", "role": "kurs muallifi", "kw": ["AI", "ИИ", "2026"], "tag_story": "left:60px;top:1240px", "tag_feed": "left:60px;top:1060px"},
    "I1-2": {"cutout": "nikita_04.png", "cut_h_story": 1220, "cut_h_feed": 860, "cut_x_feed": 600, "name": "Nikita", "role": "kurs muallifi", "kw": [], "tag_story": "left:60px;top:1260px", "tag_feed": "left:60px;top:1080px"},
    "I1-3": {"cutout": "nikita_03.png", "cut_h_story": 820, "cut_cx_story": 800, "cut_max_story": 760, "cut_h_feed": 640, "cut_x_feed": 600, "name": "Nikita", "role": "kurs muallifi", "kw": ["2"], "head_maxh_story": 520, "head_maxh_feed": 470, "tag_story": "left:70px;top:1500px", "tag_feed": "left:620px;top:560px", "tag_fixed": True},
    "I1-4": {"cutout": "nikita_09.png", "cut_h_story": 1080, "cut_max_story": 1050, "cut_h_feed": 760, "cut_x_feed": 480, "name": "Nikita", "role": "kurs muallifi", "kw": ["5", "AI", "ИИ", "2026"], "tag_story": "left:60px;top:1240px", "tag_feed": "left:60px;top:1040px"},
    "I2-1": {
        "theme": "insta", "photo": P["05"], "face_y_story": 800, "face_y_feed": 470,
        "recipe": {
            "answer": [{"font": "classic", "bg": "#151515", "fg": "#fff"}],
            "bullets": {"font": "modern", "bg": "#E8242F", "fg": "#fff", "align": "r"},
            "price": {"bg": "#FFD43B", "fg": "#111"},
            "cta": {"font": "strong", "bg": "#5DBB4A", "fg": "#fff"},
        },
    },
    "I2-2": {
        "theme": "insta", "photo": P["03"], "face_y_story": 790, "face_y_feed": 440,
        "recipe": {
            "answer": [{"font": "strong", "bg": "#E2186F", "fg": "#fff"}, {"font": "classic", "bg": "#fff", "fg": "#E2186F"}],
            "price": {"bg": "#E2186F", "fg": "#fff"},
            "cta": {"font": "strong", "bg": "#1E1A1A", "fg": "#F6D98E"},
        },
    },
    "I2-3": {
        "theme": "pink", "photo": P["04"], "face_y_story": 780,
        "recipe": {
            "answer": [{"font": "tw", "bg": "#fff", "fg": "#151515"}, {"font": "serif", "bg": "#fff", "fg": "#151515"}, {"font": "modern", "bg": "#E8242F", "fg": "#fff"}],
            "kw_color": "#E0245E",
            "cta": {"font": "strong", "bg": "#fff", "fg": "#E0245E"},
        },
    },
    "I2-4": {
        "theme": "black", "photo": P["21"], "rot": -3, "face_y_story": 820,
        "recipe": {
            "answer": [{"font": "tw", "bg": "#F9C784", "fg": "#151515"}, {"font": "tw", "bg": "#fff", "fg": "#151515"}, {"font": "classic", "bg": "#fff", "fg": "#E0245E"}],
            "kw_color": "#E0245E",
            "price": {"bg": "#5DBB4A", "fg": "#fff"},
            "cta": {"font": "strong", "bg": "#E0245E", "fg": "#fff"},
        },
    },
    "I3-1": {"layout": "blocks", "photo": P["17"], "face_y_story": 1100, "face_y_feed": 820, "shade": "linear-gradient(to bottom,rgba(0,0,0,.15),rgba(0,0,0,0) 40%,rgba(0,0,0,.25))"},
    "I3-3": {"layout": "dark", "photo": P["01"], "face_y_story": 960, "face_y_feed": 640, "zoom": 1.0, "shade": "rgba(0,0,0,.58)", "kw": ["$1000", "1000"]},
    "M1": {}, "M3": {"photo": P["04"]}, "M4": {"paper": (130, 320, 540, 725), "fs": 36}, "M5": {}, "M6": {"hole": (450, 105, 500, 190)}, "M7": {},
}

# Короткие версии (суффикс S): те же макеты, текст вдвое короче, шрифт крупнее.
SHORT = {
    "insta_qa": {"fs_story": 58, "fs_feed": 50},
    "insta_expert": {"head_fs_story": 98, "head_fs_feed": 78},
    "insta_text": {"blocks_fs_story": 100, "blocks_fs_feed": 86, "q_fs_story": 86, "q_fs_feed": 72, "it_fs_story": 72, "it_fs_feed": 60},
}


STYLE["I1-3B"] = STYLE["I1-3"]

# Вёрстка под длину строк конкретного языка. 15.10.2026 правки носителя удлинили заголовки:
# без этого «oyiga» оставалось одно на строке, а плашка I3-1/I3-1S в 9x16 наезжала на голову.
LANG_STYLE = {
    "uz": {
        "I1-2": {"head_fs_feed": 58},
        "I1-2S": {"head_fs_feed": 66},
        "I3-1": {"blocks_fs_story": 74},
        "I3-1S": {"blocks_fs_story": 90},
    },
}


def style_for(c: dict):
    if c["id"] in STYLE:
        return STYLE[c["id"]]
    base = c.get("base")
    if base in STYLE:
        return {**STYLE[base], **SHORT.get(c["type"], {})}
    return None


BUILDERS = {
    "insta_qa": build_qa, "insta_expert": build_expert, "insta_text": build_text,
    "M1": build_m1, "M3": build_m3, "M4": build_m4, "M5": build_m5, "M6": build_m6, "M7": build_m7,
}


K_AVATARS = {2: "nikita_10.png", 4: "nikita_10.png"}  # круглое фото автора на карточках 3 и 5

K_STYLE = {"2-1": {"cutout": "nikita_04.png", "cutout_last": "nikita_03.png", "hi": [5]},
           "2-1b": {"cutout": "nikita_21.png", "cutout_last": "nikita_03.png", "hi": [5], "cut_h": 820},
           "2-3": {"cutout": "nikita_09.png", "cutout_last": "nikita_03.png", "hi": [], "cut_h": 590},
           "2-4": {"cutout": "nikita_04.png", "cutout_last": "nikita_03.png", "hi": [2]}}


def build_carousels(lang: str, only: frozenset = frozenset()) -> list:
    """Карточки каруселей; only — id вида K2-1 (пусто — все карусели)."""
    jobs = []
    if lang == "uz":
        src = ROOT / "creatives_uz_type2.json"
        if not src.exists():
            return jobs
        data = json.loads(src.read_text(encoding="utf-8"))["texts"]
        texts = [{"id": x["id"], "badge": x.get("badge_uz", ""), "cta": x.get("cta_uz", ""), "headline": x.get("headline_uz", ""), "subline": x.get("subline_uz", ""),
                  "cards": [{"n": c["n"], "title": c.get("title_uz", ""), "text": c.get("text_uz", ""), "small": c.get("small_uz")} for c in x["cards"]]} for x in data]
    else:
        st = json.loads((ROOT.parent / "15-strategiya-targeta-meta" / "04-texts-static.json").read_text(encoding="utf-8"))
        t2 = [t for t in st["types"] if str(t.get("id")) == "2"][0]["texts"]
        texts = [{"id": t["id"], "badge": t.get("badge", ""), "cta": t.get("cta", ""), "headline": t.get("headline", ""), "subline": t.get("subline", ""), "cards": t["cards"]} for t in t2 if t["id"] in K_STYLE]
    for t in texts:
        ks = K_STYLE.get(t["id"])
        if not ks or (only and f"K{t['id']}" not in only):
            continue
        t = dict(t, **{k: v for k, v in ks.items() if k.startswith("cut")})
        cards = list(t["cards"])
        if cards and t.get("headline") and cards[0].get("title", "").strip() != t["headline"].strip():
            cards = [{"n": 0, "title": t["headline"], "text": t.get("subline", "")}] + cards
        if len(cards) < 3:
            continue
        for i, card in enumerate(cards):
            card = dict(card)
            if card.get("n") in ks["hi"]:
                card["highlight"] = True
            hp = OUT_HTML / f"K{t['id']}_{i + 1}_{lang}.html"
            hp.write_text(build_k_card(t, card, i, len(cards), lang), encoding="utf-8")
            jobs.append({"html": str(hp), "out": str(ROOT / "render" / lang / f"K{t['id']}_card{i + 1}.png"), "w": 1080, "h": 1080})
    return jobs


SRC_OVERRIDE = {}


def load(lang: str):
    src = SRC_OVERRIDE.get("main") or ROOT / ("creatives_uz.json" if lang == "uz" else "creatives_ru.json")
    data = json.loads(src.read_text(encoding="utf-8"))
    key = "fields_uz" if lang == "uz" else "fields_ru"
    return [(c, c[key]) for c in data["creatives"] if key in c]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--only", default="")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--src", default="")
    ap.add_argument("--outdir", default="")
    a = ap.parse_args()
    if a.src:
        SRC_OVERRIDE["main"] = Path(a.src)
    only = set(filter(None, a.only.split(",")))
    OUT_HTML.mkdir(parents=True, exist_ok=True)
    jobs = []
    for c, f in load(a.lang):
        cid = c["id"]
        if only and cid not in only:
            continue
        b = BUILDERS.get(c["type"]) or BUILDERS.get(cid)
        st = style_for(c)
        if not b or st is None:
            continue
        st = {**st, **LANG_STYLE.get(a.lang, {}).get(cid, {})}
        for fmt, (w, h) in FORMATS.items():
            html_path = OUT_HTML / f"{cid}_{fmt}_{a.lang}.html"
            html_path.write_text(b(c, f, fmt, st), encoding="utf-8")
            jobs.append({"html": str(html_path), "out": str(ROOT / "render" / (a.outdir or a.lang) / f"{cid}_{fmt}.png"), "w": w, "h": h})
    if (not only and not a.src) or any(x.startswith("K") for x in only):
        jobs += build_carousels(a.lang, frozenset(x for x in only if x.startswith("K")))
    jf = ROOT / "render" / f"jobs_{a.lang}.json"
    jf.parent.mkdir(parents=True, exist_ok=True)
    jf.write_text(json.dumps(jobs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(jobs), "html")
    if a.render:
        subprocess.run([sys.executable, str(ROOT / "render.py"), "--batch", str(jf)], check=True)


if __name__ == "__main__":
    main()
