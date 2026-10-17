"""Видео-креативы: HTML-анимация → кадры (Playwright) → MP4 (ffmpeg).

python3 video.py --lang uz|ru --only V2,M2,V1 [--fmt story,feed] [--preview]
Страница обязана определить window.setT(t) и window.DURATION. Кадры — 30 fps.
"""
import argparse
import asyncio
import json
import subprocess
from pathlib import Path

from playwright.async_api import async_playwright

import build as B

ROOT = B.ROOT
FPS = 30
OUT = ROOT / "render"


# ---------------------------------------------------------------- общий рендер

async def render_video(html_path: Path, out_mp4: Path, w: int, h: int, audio: Path = None, preview: bool = False, audio_fn=None):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        await page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        await page.wait_for_selector("body[data-ready]", timeout=15000)
        dur = await page.evaluate("window.DURATION")
        write = await page.evaluate("window.WRITE || []")
        if audio_fn:
            audio_fn(dur, write)
        n = int(dur * FPS)
        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_mp4.with_suffix(".noaudio.mp4")
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium", "-r", str(FPS), str(tmp)]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = range(0, n, 10) if preview else range(n)
        for i in frames:
            await page.evaluate(f"window.setT({i / FPS:.5f})")
            buf = await page.screenshot(type="jpeg", quality=93)
            ff.stdin.write(buf)
        ff.stdin.close()
        ff.wait()
        await browser.close()
    if audio and audio.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                        "-t", f"{dur:.3f}", "-movflags", "+faststart", str(out_mp4)], check=True)
        tmp.unlink()
    else:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-c", "copy", "-movflags", "+faststart", str(out_mp4)], check=True)
        tmp.unlink()
    print("video ok", out_mp4.name, f"{dur}s")


async def snap(html_path: Path, times: list, outdir: Path, prefix: str, w: int, h: int):
    outdir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": w, "height": h})
        await page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        await page.wait_for_selector("body[data-ready]", timeout=15000)
        for t in times:
            await page.evaluate(f"window.setT({t})")
            await page.screenshot(path=str(outdir / f"{prefix}_{t:05.2f}.png"))
        await browser.close()
    print("snaps", prefix, times)


def synth_scribble(out: Path, intervals: list, dur: float):
    gate = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in intervals) or "0"
    fc = (f"anoisesrc=d={dur}:c=white:a=0.5:r=44100,bandpass=f=3200:width_type=h:w=2600,tremolo=f=17:d=0.75,"
          f"volume='0.95*min(1,{gate})':eval=frame,lowpass=f=7000[out]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-filter_complex", fc, "-map", "[out]", "-ac", "2", "-ar", "44100", "-t", str(dur), str(out)], check=True)


def synth_audio(out: Path, events: list, dur: float):
    """events: [(t, kind)], kind: ding | whoosh | pop. Синтез через ffmpeg lavfi."""
    srcs, labels = [], []
    for i, (t, kind) in enumerate(events):
        ms = int(t * 1000)
        if kind == "ding":
            e = "0.55*sin(2*PI*1318.5*t)*exp(-7*t)+0.35*sin(2*PI*1975.5*t)*exp(-9*t)*gt(t,0.09)+0.15*sin(2*PI*2637*t)*exp(-12*t)"
            srcs.append(f"aevalsrc='{e}':s=44100:d=0.9,adelay={ms}|{ms}[a{i}]")
        elif kind == "whoosh":
            srcs.append(f"anoisesrc=d=0.6:c=pink:a=0.35:r=44100,highpass=f=500,lowpass=f=5000,afade=t=in:d=0.25,afade=t=out:st=0.3:d=0.3,adelay={ms}|{ms}[a{i}]")
        elif kind == "pop":
            e = "0.6*sin(2*PI*(420+900*exp(-30*t))*t)*exp(-14*t)"
            srcs.append(f"aevalsrc='{e}':s=44100:d=0.4,adelay={ms}|{ms}[a{i}]")
        labels.append(f"[a{i}]")
    srcs.insert(0, f"anullsrc=r=44100:cl=stereo:d={dur}[base]")
    labels.insert(0, "[base]")
    fc = ";".join(srcs) + ";" + "".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=first,volume=0.9[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-filter_complex", fc, "-map", "[out]", "-ac", "2", "-ar", "44100", str(out)], check=True)


TIMELINE_JS = """
<script>
function clamp(x,a,b){return Math.max(a,Math.min(b,x))}
function ease(x){return x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2}
function spring(x){x=clamp(x,0,1);return 1-Math.cos(x*Math.PI*2.2)*Math.exp(-5.5*x)}
function prog(t,a,b){return clamp((t-a)/(b-a),0,1)}
</script>
"""


# ---------------------------------------------------------------- V2 уведомления на экране iPhone

V2_CSS = """
body{background:#000;font-family:-apple-system,'SF Pro Display','SF Pro Text','Helvetica Neue',Inter,sans-serif}
#lock{position:absolute;inset:0;transform-origin:50% 40%}
#wall{position:absolute;inset:0}
#wall:after{content:'';position:absolute;inset:0;background:linear-gradient(to bottom,rgba(0,0,0,.25),rgba(0,0,0,0) 35%,rgba(0,0,0,.2))}
.sb{position:absolute;top:38px;left:80px;right:70px;display:flex;justify-content:space-between;align-items:center;color:#fff;font-weight:600;font-size:42px}
.sb .ic{display:flex;gap:16px;align-items:center}
.lockic{position:absolute;top:120px;left:50%;transform:translateX(-50%)}
.date{position:absolute;top:210px;width:100%;text-align:center;color:rgba(255,255,255,.92);font-weight:600;font-size:56px;letter-spacing:.01em}
.time{position:absolute;top:262px;width:100%;text-align:center;color:rgba(255,255,255,.96);font-weight:700;font-size:270px;letter-spacing:-.02em;line-height:1}
.n{position:absolute;left:34px;right:34px;border-radius:56px;padding:34px 36px;display:flex;gap:30px;align-items:center;
   background:rgba(246,246,246,.80);-webkit-backdrop-filter:blur(40px) saturate(1.8);backdrop-filter:blur(40px) saturate(1.8);color:#111;box-shadow:0 10px 40px rgba(0,0,0,.18)}
.n .ai{width:108px;height:108px;border-radius:26px;flex:none;display:flex;align-items:center;justify-content:center}
.n .tx{flex:1;min-width:0}
.n .hd{display:flex;justify-content:space-between;align-items:baseline}
.n .ti{font-weight:700;font-size:42px}
.n .tm{font-size:34px;color:rgba(60,60,67,.6)}
.n .bd{font-size:41px;line-height:1.24;margin-top:4px}
.btm{position:absolute;bottom:120px;width:142px;height:142px;border-radius:50%;background:rgba(30,30,30,.45);-webkit-backdrop-filter:blur(20px);backdrop-filter:blur(20px);display:flex;align-items:center;justify-content:center}
.home{position:absolute;bottom:26px;left:50%;width:390px;height:15px;margin-left:-195px;border-radius:10px;background:#fff}
#dim{position:absolute;inset:0;background:rgba(0,0,0,.62);opacity:0}
#cap{position:absolute;left:70px;right:70px;top:560px;text-align:center;color:#fff;opacity:0}
#cap .t{font:900 92px/1.08 Montserrat,sans-serif;text-transform:none}
#cap .t span{color:#FFD43B}
#cta{position:absolute;left:0;right:0;top:1300px;text-align:center;opacity:0}
#cta span{display:inline-block;max-width:900px;background:#5DBB4A;color:#fff;font:800 50px/1.2 Montserrat,sans-serif;padding:28px 50px;border-radius:999px;box-shadow:0 14px 40px rgba(93,187,74,.45)}
.feed .date{top:120px;font-size:46px}.feed .time{top:160px;font-size:200px}.feed .lockic{top:70px}.feed .btm{display:none}#cap.feed{top:250px}#cap.feed .t{font-size:80px}#cta.feed{top:960px}
"""

ICON_BANK = '<div class="ai" style="background:linear-gradient(135deg,#7B2FF7,#9F44FF)"><svg width="62" height="62" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><rect x="2.5" y="5" width="19" height="14" rx="2.5"/><path d="M2.5 10h19"/><path d="M6 15h4"/></svg></div>'
ICON_CHAT = '<div class="ai" style="background:linear-gradient(180deg,#5BE36E,#26C04A)"><svg width="66" height="66" viewBox="0 0 24 24" fill="#fff"><path d="M12 3C6.5 3 2 6.6 2 11c0 2.5 1.4 4.7 3.7 6.2L5 21l4.1-2.3c.9.2 1.9.3 2.9.3 5.5 0 10-3.6 10-8s-4.5-8-10-8z"/></svg></div>'
ICON_TG = '<div class="ai" style="background:linear-gradient(180deg,#38B0E3,#1D93D2);border-radius:50%"><svg width="62" height="62" viewBox="0 0 24 24" fill="#fff"><path d="M21.5 3.6 2.9 10.8c-1.2.5-1.2 1.2-.2 1.5l4.7 1.5 1.8 5.6c.2.6.1.9.8.9.5 0 .7-.2 1-.5l2.3-2.2 4.8 3.5c.9.5 1.5.2 1.7-.8l3.1-14.6c.3-1.3-.5-1.9-1.4-1.6zM8.6 13.4l9.6-6.1c.5-.3.9-.1.5.2l-8 7.2-.3 3.4-1.8-4.7z"/></svg></div>'


def v2_html(f: dict, fmt: str) -> str:
    w, h = B.FORMATS[fmt]
    wall = B.photo_bg(B.P["21"], w, h, 980 if fmt == "story" else 700)
    sb = ('<div class="sb"><span>Ucell</span><span class="ic">'
          '<svg width="54" height="34" viewBox="0 0 18 12" fill="#fff"><rect x="0" y="8" width="3" height="4" rx="1"/><rect x="5" y="5.5" width="3" height="6.5" rx="1"/><rect x="10" y="3" width="3" height="9" rx="1"/><rect x="15" y="0" width="3" height="12" rx="1"/></svg>'
          '<svg width="50" height="36" viewBox="0 0 16 12" fill="#fff"><path d="M8 11.5 5.6 9a3.4 3.4 0 0 1 4.8 0zM3.4 6.8a6.6 6.6 0 0 1 9.2 0l-1.4 1.4a4.6 4.6 0 0 0-6.4 0zM1.2 4.6a9.7 9.7 0 0 1 13.6 0l-1.4 1.4a7.7 7.7 0 0 0-10.8 0z"/></svg>'
          '<svg width="84" height="40" viewBox="0 0 28 13"><rect x=".5" y=".5" width="24" height="12" rx="3.5" fill="none" stroke="rgba(255,255,255,.5)"/><rect x="2" y="2" width="17" height="9" rx="2" fill="#fff"/><rect x="25.5" y="4.5" width="2" height="4" rx="1" fill="rgba(255,255,255,.5)"/></svg>'
          "</span></div>")
    lock = '<svg class="lockic" width="40" height="52" viewBox="0 0 20 26"><rect x="1" y="11" width="18" height="14" rx="3" fill="#fff"/><path d="M5 11V7a5 5 0 0 1 10 0v4" fill="none" stroke="#fff" stroke-width="2.6"/></svg>'
    notifs = [
        (ICON_BANK, f["notif_bank_title"], f["notif_bank"]),
        (ICON_CHAT, f["notif_client_title"], f["notif_client"]),
        (ICON_TG, f["notif_tg_title"], f["notif_tg"]),
    ]
    cards = "".join(
        f'<div class="n" id="n{i}" style="opacity:0">{ic}<div class="tx"><div class="hd"><span class="ti">{B.esc(t)}</span><span class="tm">{B.esc(f.get("now","hozir"))}</span></div><div class="bd">{B.esc(b)}</div></div></div>'
        for i, (ic, t, b) in enumerate(notifs)
    )
    bottom = ('<div class="btm" style="left:96px"><svg width="54" height="70" viewBox="0 0 12 16" fill="#fff"><path d="M3 0h6v3l-1.5 2v10H4.5V5L3 3z"/></svg></div>'
              '<div class="btm" style="right:96px"><svg width="68" height="56" viewBox="0 0 24 20" fill="#fff"><path d="M8.5 1h7l1.8 2.5H21a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V5.5a2 2 0 0 1 2-2h3.7z"/><circle cx="12" cy="11" r="4.2" fill="#555"/></svg></div>'
              '<div class="home"></div>')
    cap = B.mark(f["caption"], [], "x")
    cap = cap.replace('<span class="x">', "<span>")
    top0 = 800 if fmt == "story" else 470
    body = (
        f'<div id="lock" class="{fmt}"><div id="wall" style="{wall}"></div>{sb}{lock}'
        f'<div class="date">{B.esc(f["date"])}</div><div class="time">21:41</div>{cards}{bottom}</div>'
        f'<div id="dim"></div><div id="cap" class="{fmt}"><div class="t" data-box data-maxh="{620 if fmt == "story" else 480}">{cap}</div></div>'
        f'<div id="cta" class="{fmt}"><span>{B.esc(f["cta"])} ⬇️</span></div>'
    )
    js = f"""
<script>
window.DURATION = 12.0;
const T0 = [1.0, 3.0, 5.0];
const TOP = {top0};
const GAP = 22;
function setT(t){{
  const cards = [0,1,2].map(i => document.getElementById('n'+i));
  const hs = cards.map(c => c.offsetHeight);
  // новые сверху: позиция = сумма высот более новых карточек, которые уже появились
  cards.forEach((c, i) => {{
    const p = prog(t, T0[i], T0[i] + .55);
    let y = TOP;
    for (let j = i + 1; j < 3; j++) {{ y += (hs[j] + GAP) * ease(prog(t, T0[j], T0[j] + .45)); }}
    const sp = spring(p);
    c.style.opacity = clamp(p * 2.5, 0, 1);
    c.style.top = (y + (1 - sp) * 140) + 'px';
    c.style.transform = 'scale(' + (0.92 + 0.08 * sp) + ')';
  }});
  const lock = document.getElementById('lock');
  const z = 1 + 0.03 * prog(t, 0, 7);
  const d = prog(t, 7.0, 7.6);
  lock.style.transform = 'scale(' + (z + 0.04 * ease(d)) + ')';
  lock.style.filter = 'blur(' + (10 * ease(d)) + 'px)';
  document.getElementById('dim').style.opacity = ease(d);
  const c = prog(t, 7.3, 7.9), cs = spring(c);
  const cap = document.getElementById('cap');
  cap.style.opacity = clamp(c * 2, 0, 1); cap.style.transform = 'translateY(' + ((1 - cs) * 60) + 'px)';
  const k = prog(t, 8.6, 9.1), ks = spring(k);
  const cta = document.getElementById('cta');
  cta.style.opacity = clamp(k * 2, 0, 1);
  const pulse = t > 9.1 ? 1 + 0.04 * Math.sin((t - 9.1) * 6.3) : 1;
  cta.style.transform = 'scale(' + ((0.7 + 0.3 * ks) * pulse) + ')';
}}
window.setT = setT;
document.fonts.ready.then(() => {{ setT(0); }});
</script>
"""
    return B.page(w, h, V2_CSS, body).replace("</body>", TIMELINE_JS + js + "</body>")


# ---------------------------------------------------------------- M2 пишем от руки

M2_CSS = """
body{background:#FBFAF6}
#paper{position:absolute;inset:0;background:radial-gradient(130% 90% at 50% 40%,#FFFFFF 0%,#FAF8F3 70%,#F1EEE6 100%)}
#grain{position:absolute;inset:0;opacity:.32;mix-blend-mode:multiply}
.ln{position:absolute;white-space:nowrap;color:#151515;font-family:Caveat,cursive;line-height:1.05;padding-right:.18em}
.ln .box{position:relative}
svg.doodle{position:absolute;left:0;top:0;overflow:visible;pointer-events:none}
svg.doodle path{fill:none;stroke:#151515;stroke-linecap:round;stroke-linejoin:round}
#hl path{stroke:#FF5FA2;opacity:.38;stroke-linecap:butt}
#pen{position:absolute;left:0;top:0;width:10px;height:10px;overflow:visible;filter:drop-shadow(18px 22px 14px rgba(0,0,0,.22))}
"""


def m2_html(f: dict, fmt: str) -> str:
    w, h = B.FORMATS[fmt]
    story = fmt == "story"
    blocks = json.dumps(f["blocks"], ensure_ascii=False)
    pen = (
        '<svg id="pen" width="10" height="10" style="overflow:visible"><g transform="rotate(32)">'
        '<path d="M0 0 L-9 -34 L9 -34 Z" fill="#111"/>'
        '<rect x="-17" y="-120" width="34" height="88" rx="6" fill="#1b1b1b"/>'
        '<rect x="-19" y="-520" width="38" height="404" rx="14" fill="url(#pg)"/>'
        '<rect x="-21" y="-560" width="42" height="70" rx="12" fill="#111"/>'
        '<rect x="-4" y="-470" width="8" height="300" rx="4" fill="rgba(255,255,255,.55)"/>'
        '<defs><linearGradient id="pg" x1="0" x2="1"><stop offset="0" stop-color="#cfd3d8"/><stop offset=".5" stop-color="#f7f8fa"/><stop offset="1" stop-color="#b9bec4"/></linearGradient></defs>'
        "</g></svg>"
    )
    grain = '<svg id="grain" width="100%" height="100%"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 .5  0 0 0 0 .45  0 0 0 0 .4  0 0 0 .35 0"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>'
    area = {"x": 70, "y": 250 if story else 70, "w": 940, "h": 1330 if story else 1210}
    body = f'<div id="paper"></div>{grain}<div id="lines"></div><svg class="doodle" id="dd" width="{w}" height="{h}"></svg><svg class="doodle" id="hl" width="{w}" height="{h}"></svg>{pen}'
    js = """
<script>
const BLOCKS = __BLOCKS__; const AREA = __AREA__; const SPEED = __SPEED__;
window.DURATION = 0; window.WRITE = [];
const L = []; const D = [];
function mk(tag, attrs){ const e=document.createElementNS('http://www.w3.org/2000/svg', tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }
function wrapWords(text, fontCss, maxW){
  const c = document.createElement('canvas').getContext('2d'); c.font = fontCss;
  const words = text.split(' '); const lines = []; let cur = '';
  for (const wd of words){ const t = cur ? cur + ' ' + wd : wd; if (c.measureText(t.replace(/[\[\]~=]/g,'')).width > maxW && cur){ lines.push(cur); cur = wd; } else cur = t; }
  if (cur) lines.push(cur); return lines;
}
function markup(s){
  return s.replace(/~~(.+?)~~/g,'<span class="strk">$1</span>').replace(/\[\[(.+?)\]\]/g,'<span class="box">$1</span>').replace(/==(.+?)==/g,'<span class="hlt">$1</span>');
}
function layout(scale){
  const host = document.getElementById('lines'); host.innerHTML=''; L.length = 0;
  let y = AREA.y;
  for (const b of BLOCKS){
    const size = b.size * scale; const font = `${b.weight||600} ${size}px Caveat`;
    y += (b.gap||0) * scale;
    const lines = b.nowrap ? [b.text] : wrapWords(b.text, font, (AREA.w - (b.indent||0)) * 0.93);
    for (const ln of lines){
      const d = document.createElement('div'); d.className='ln'; d.style.font = font; d.style.lineHeight='1.08';
      d.innerHTML = markup(ln); host.appendChild(d);
      const wpx = d.offsetWidth; let x = AREA.x + (b.indent||0);
      if (b.align === 'center') x = AREA.x + (AREA.w - wpx)/2; if (b.align === 'right') x = AREA.x + AREA.w - wpx;
      d.style.left = x + 'px'; d.style.top = y + 'px';
      L.push({el:d, x, y, w:wpx, h:d.offsetHeight, block:b});
      y += d.offsetHeight * 0.98;
    }
    if (b.downs) y += 140 * scale;
  }
  return y;
}
function build(){
  let scale = 1; let bottom = layout(scale);
  while (bottom > AREA.y + AREA.h && scale > .5){ scale *= .96; bottom = layout(scale); }
  const shift = (AREA.y + AREA.h - bottom) / 2; L.forEach(o => { o.y += shift; o.el.style.top = o.y + 'px'; });
  const dd = document.getElementById('dd'), hl = document.getElementById('hl');
  const add = (svg, d, w, dur, extra) => { const p = mk('path', {d, 'stroke-width': w}); svg.appendChild(p); const o = Object.assign({p, dur}, extra||{}); D.push(o); return o; };
  let t = 0.6; const HL = [];
  L.forEach((o, i) => {
    const b = o.block; const last = !L[i+1] || L[i+1].block !== b;
    o.t0 = t; o.t1 = t + Math.max(.45, o.w / SPEED); t = o.t1 + .12;
    const seq = [];
    o.el.querySelectorAll('.strk').forEach(sp => { const q = sp.getBoundingClientRect(); seq.push(add(dd, `M${q.left-8} ${q.top+q.height*.62} C ${q.left+q.width*.3} ${q.top+q.height*.5}, ${q.left+q.width*.7} ${q.top+q.height*.68}, ${q.right+10} ${q.top+q.height*.52}`, 7, .45)); });
    o.el.querySelectorAll('.box').forEach(sp => { const q = sp.getBoundingClientRect(); const x0=q.left-18,y0=q.top+6,x1=q.right+18,y1=q.bottom-4; seq.push(add(dd, `M${x0+12} ${y0} L${x1} ${y0+5} L${x1-5} ${y1} L${x0} ${y1-4} L${x0+6} ${y0-12}`, 6, .7)); });
    o.el.querySelectorAll('.hlt').forEach(sp => { const q = sp.getBoundingClientRect(); HL.push(add(hl, `M${q.left-6} ${q.top+q.height*.64} L${q.right+6} ${q.top+q.height*.6}`, q.height*.55, .5, {hl:true})); });
    if (last && b.underline){ seq.push(add(dd, `M${o.x} ${o.y+o.h*.98} q ${o.w*.25} -14 ${o.w*.5} 0 t ${o.w*.5} 0`, 6, .6)); }
    if (last && b.arrow){ const x=o.x+o.w+24, y=o.y+o.h*.58; seq.push(add(dd, `M${x} ${y} C ${x+40} ${y-30}, ${x+80} ${y+10}, ${x+120} ${y-6} M${x+92} ${y-34} L${x+122} ${y-6} L${x+88} ${y+18}`, 6, .55)); }
    if (last && b.star){ const x=Math.min(o.x+o.w+50, AREA.x+AREA.w-20), y=o.y+o.h*.35; seq.push(add(dd, `M${x} ${y-34} L${x+10} ${y-6} L${x+40} ${y-4} L${x+16} ${y+14} L${x+26} ${y+44} L${x} ${y+26} L${x-26} ${y+44} L${x-16} ${y+14} L${x-40} ${y-4} L${x-10} ${y-6} Z`, 5, .6)); }
    if (last && b.downs){ for (let k=0;k<3;k++){ const x = AREA.x + AREA.w/2 + (k-1)*110, y = o.y + o.h + 24; seq.push(add(dd, `M${x} ${y} L${x} ${y+86} M${x-26} ${y+58} L${x} ${y+88} L${x+26} ${y+58}`, 7, .32)); } }
    seq.forEach(d => { d.t0 = t; t += d.dur + .08; });
    t += (last ? .3 : .05) + (b.pause||0);
  });
  HL.forEach((d, k) => { d.t0 = t + .2 + k * .5; });
  const endT = t + .2 + HL.length * .5;
  D.forEach(d => { const len = d.p.getTotalLength(); d.len = len; d.p.style.strokeDasharray = len; d.p.style.strokeDashoffset = len; });
  window.DURATION = Math.ceil((endT + 2.6) * 10) / 10;
  window.WRITE = L.map(o => [o.t0, o.t1]).concat(D.filter(d => !d.hl).map(d => [d.t0, d.t0 + d.dur]));
}
function penAt(t){
  // где перо: пишет строку, рисует дудл или едет к следующей
  for (const o of L){ if (t >= o.t0 && t <= o.t1){ const p = (t - o.t0)/(o.t1 - o.t0); return [o.x + p*o.w, o.y + o.h*.78 + 6*Math.sin(t*38) - 10*Math.abs(Math.sin(t*9))]; } }
  for (const d of D){ if (t >= d.t0 && t <= d.t0 + d.dur){ const p = (t - d.t0)/d.dur; const pt = d.p.getPointAtLength(p*d.len); return [pt.x, pt.y]; } }
  // между — плавно к следующему старту
  const ev = [...L.map(o => ({t0:o.t0, t1:o.t1, a:[o.x, o.y+o.h*.78], b:[o.x+o.w, o.y+o.h*.78]})), ...D.map(d => ({t0:d.t0, t1:d.t0+d.dur, a:[d.p.getPointAtLength(0).x, d.p.getPointAtLength(0).y], b:[d.p.getPointAtLength(d.len).x, d.p.getPointAtLength(d.len).y]}))].sort((x,y) => x.t0 - y.t0);
  let prev = null, next = null; for (const e of ev){ if (e.t1 <= t) prev = e; else if (e.t0 > t){ next = e; break; } }
  if (!next) return prev ? [prev.b[0] + 700*ease(clamp((t-prev.t1)/1.0,0,1)), prev.b[1] + 1000*ease(clamp((t-prev.t1)/1.0,0,1))] : [AREA.x, AREA.y];
  if (!prev) return [next.a[0] + 300*(1-clamp(t/next.t0,0,1)), next.a[1] + 500*(1-clamp(t/next.t0,0,1))];
  const p = ease(clamp((t - prev.t1)/(next.t0 - prev.t1), 0, 1));
  return [prev.b[0] + (next.a[0]-prev.b[0])*p, prev.b[1] + (next.a[1]-prev.b[1])*p - 40*Math.sin(p*Math.PI)];
}
function setT(t){
  for (const o of L){ const p = clamp((t - o.t0)/(o.t1 - o.t0), 0, 1); o.el.style.clipPath = p >= 1 ? 'none' : `inset(-20px ${(1-p)*100}% -30px -10px)`; o.el.style.visibility = p > 0 ? 'visible' : 'hidden'; }
  for (const d of D){ const p = clamp((t - d.t0)/d.dur, 0, 1); d.p.style.strokeDashoffset = d.len * (1 - p); }
  const [x, y] = penAt(t); const pen = document.getElementById('pen'); pen.style.transform = `translate(${x}px, ${y}px)`;
}
window.setT = setT;
Promise.all(['500','600','700'].map(wt => document.fonts.load(wt + ' 80px Caveat', 'АБВabcʻ‘’$0'))).then(() => document.fonts.ready).then(() => { build(); setT(0); document.body.dataset.ready = 1; });
</script>
""".replace("__BLOCKS__", blocks).replace("__AREA__", json.dumps(area)).replace("__SPEED__", str(700 if story else 640))
    html_doc = B.page(w, h, M2_CSS, body)
    html_doc = html_doc.replace("document.body.dataset.ready = 1;\n});\n</script>", "});\n</script>", 1)
    return html_doc.replace("</body>", TIMELINE_JS + js + "</body>")


# ---------------------------------------------------------------- V1 моушн-монтаж «этот ролик сделал ИИ»

V1_CSS = """
body{background:#07070D;color:#fff;font-family:Montserrat,sans-serif}
#bg{position:absolute;inset:-10%;}
.blob{position:absolute;border-radius:50%;filter:blur(90px);opacity:.75}
#grid{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.06) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.06) 1px,transparent 1px);background-size:90px 90px}
.sc{position:absolute;inset:0;opacity:0;will-change:transform,filter,opacity}
.big{position:absolute;left:70px;right:70px;text-align:center;font:900 1em/1.04 Montserrat,sans-serif;text-transform:uppercase;letter-spacing:-.01em}
.a1{color:#9B7BFF}.a2{color:#21E6C1}.a3{color:#FFD43B}

.phone{position:absolute;width:300px;height:600px;border-radius:44px;background:#111;border:8px solid #222;overflow:hidden;box-shadow:0 30px 60px rgba(0,0,0,.5)}
.phone .ph{position:absolute;inset:0;background-size:cover;background-position:center}
.phone .rl{position:absolute;left:18px;bottom:22px;right:18px;font:800 24px/1.2 Montserrat;color:#fff;text-shadow:0 2px 8px rgba(0,0,0,.6)}
.stamp{position:absolute;font:900 240px/1 Montserrat;color:#FFD43B;text-shadow:0 10px 40px rgba(255,212,59,.45)}
.chip{position:absolute;left:50%;padding:26px 54px;border-radius:999px;border:4px solid rgba(255,255,255,.85);font:800 60px/1 Montserrat;white-space:nowrap;transform:translateX(-50%)}
.chip i{position:absolute;left:-6%;right:-6%;top:50%;height:10px;background:#FF3B5C;border-radius:6px;transform-origin:left center}
.clock{position:absolute;left:50%;width:360px;height:360px;margin-left:-180px;border-radius:50%;border:16px solid #21E6C1;box-shadow:0 0 60px rgba(33,230,193,.45)}
.hand{position:absolute;left:50%;top:50%;width:14px;margin-left:-7px;background:#fff;border-radius:8px;transform-origin:50% 100%}
.full{position:absolute;inset:0;background-size:cover;background-position:center}
.shade{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(7,7,13,.15),rgba(7,7,13,.15) 35%,rgba(7,7,13,.92) 70%)}
.chk{position:absolute;left:90px;right:60px;display:flex;align-items:center;gap:34px;font:800 76px/1.1 Montserrat}
.chk b{flex:none;width:96px;height:96px;border-radius:24px;background:#21E6C1;color:#07070D;display:flex;align-items:center;justify-content:center;font:900 64px Montserrat}
.btn{position:absolute;left:50%;transform:translateX(-50%);background:linear-gradient(90deg,#7C5CFF,#21E6C1);padding:36px 70px;border-radius:999px;font:900 58px/1 Montserrat;color:#07070D;white-space:nowrap;box-shadow:0 20px 60px rgba(124,92,255,.5)}
.cd{position:absolute;left:0;right:0;text-align:center;font:900 190px/1 'Roboto Condensed',sans-serif;letter-spacing:.02em;color:#fff}
#flash{position:absolute;inset:0;background:#fff;opacity:0}
#scan{position:absolute;inset:0;background:repeating-linear-gradient(0deg,rgba(255,255,255,.035) 0 2px,transparent 2px 5px);mix-blend-mode:overlay}
"""


def v1_html(f: dict, fmt: str) -> str:
    w, h = B.FORMATS[fmt]
    story = fmt == "story"
    k = 1.0 if story else 0.8
    S = f["scenes"]
    bl = f["bullets"]
    C = f["cta_scenes"]
    site_ph = B.ASSETS / "site_phone.png"
    ph = [B.uri(site_ph if site_ph.exists() else B.P["03"]), B.uri(B.P["04"]), B.uri(B.P["21"])]
    cy = h / 2
    body = (
        '<div id="bg"><div class="blob" id="b1" style="width:900px;height:900px;background:#5B3CFF"></div>'
        '<div class="blob" id="b2" style="width:800px;height:800px;background:#00C9A7"></div>'
        '<div class="blob" id="b3" style="width:700px;height:700px;background:#FF3B8D"></div></div><div id="grid"></div>'
        # S1
        f'<div class="sc" id="s1"><div class="big glitch" id="g1" style="top:{cy - 260 * k}px;font-size:{128 * k}px" data-box data-maxh="{560 * k}" data-maxw="945">{B.esc(S[0])}</div></div>'
        # S2
        f'<div class="sc" id="s2"><div class="big" style="top:{(260 if story else 60)}px;font-size:{84 * k}px" data-box data-maxh="{330 * k}">{B.mark(S[1], [], "a3")}</div>'
        + "".join(f'<div class="phone" id="p{i}" style="left:{[60, 390, 720][i]}px;top:{(820 if story else 560) - (40 if i == 1 else 0)}px;transform:scale({k})"><div class="ph" style="background-image:url({ph[i]});background-position:{"top center" if i == 0 else "center"}"></div><div class="rl">{["SAYT", "BOT", "REELS"][i]}</div></div>' for i in range(3))
        + f'<div class="stamp" id="st" style="left:0;right:0;text-align:center;top:{(1380 if story else 980)}px;font-size:{240 * k}px">$100</div></div>'
        # S3
        f'<div class="sc" id="s3"><div class="big" style="top:{(280 if story else 70)}px;font-size:{78 * k}px" data-box data-maxh="{420 * k}">{B.esc(S[2])}</div>'
        + "".join(f'<div class="chip" id="c{i}" style="top:{(860 if story else 560) + i * 190 * k}px;font-size:{60 * k}px">{B.esc(x)}<i></i></div>' for i, x in enumerate(f["chips"]))
        + "</div>"
        # S4
        f'<div class="sc" id="s4"><div class="clock" style="top:{(520 if story else 300)}px"><div class="hand" id="hh" style="height:110px;margin-top:-110px"></div><div class="hand" id="mh" style="height:150px;margin-top:-150px;background:#21E6C1"></div></div>'
        f'<div class="big" style="top:{(1020 if story else 760)}px;font-size:{100 * k}px" data-box data-maxh="{400 * k}">{B.mark(S[3], f.get("kw4", []), "a2")}</div></div>'
        # S5
        f'<div class="sc" id="s5"><div class="full" id="f5" style="background-image:url({B.uri(B.P["17"])})"></div><div class="shade"></div>'
        f'<div class="big" style="top:{(1020 if story else 700)}px;font-size:{80 * k}px" data-box data-maxh="{520 * k}" data-maxw="945">{B.mark(S[4], f.get("kw5", []), "a3")}</div></div>'
        # S6
        f'<div class="sc" id="s6">' + "".join(f'<div class="chk" id="k{i}" style="top:{(520 if story else 300) + i * 250 * k}px;font-size:{76 * k}px"><b>✓</b><span>{B.esc(x)}</span></div>' for i, x in enumerate(bl)) + "</div>"
        # S7
        f'<div class="sc" id="s7"><div class="big" style="top:{(330 if story else 90)}px;font-size:{84 * k}px" data-box data-maxh="{520 * k}">{B.esc(C[0])}</div>'
        f'<div class="btn" id="bt" style="top:{(1050 if story else 760)}px;font-size:{68 * k}px">{B.esc(f["button"])}</div>'
        f'<div class="big" id="ar" style="top:{(1230 if story else 900)}px;font-size:{160 * k}px">⬇️</div></div>'
        # S8
        f'<div class="sc" id="s8"><div class="cd" id="cd" style="top:{(470 if story else 230)}px;font-size:{190 * k}px">23:59:59</div>'
        f'<div class="big" style="top:{(760 if story else 470)}px;font-size:{70 * k}px" data-box data-maxh="{560 * k}">{B.mark(C[1], [], "a3")}</div></div>'
        # S9
        f'<div class="sc" id="s9"><div class="big" id="kl" style="top:{cy - 200 * k}px;font-size:{230 * k}px">{B.esc(C[2])}</div>'
        f'<div class="big" id="ar2" style="top:{cy + 120 * k}px;font-size:{170 * k}px">⬇️</div></div>'
        '<div id="scan"></div><div id="flash"></div>'
    )
    js = """
<script>
window.DURATION = 17.0;
const SC = [[1,0,1.8],[2,1.8,3.6],[3,3.6,5.6],[4,5.6,7.0],[5,7.0,9.6],[6,9.6,11.6],[7,11.6,13.6],[8,13.6,15.6],[9,15.6,17.0]];
const $ = id => document.getElementById(id);
function setT(t){
  // фон
  $('b1').style.transform = `translate(${-100 + 220*Math.sin(t*.7)}px, ${200 + 160*Math.cos(t*.5)}px)`;
  $('b2').style.transform = `translate(${500 + 200*Math.cos(t*.6)}px, ${900 + 220*Math.sin(t*.8)}px)`;
  $('b3').style.transform = `translate(${300 + 260*Math.sin(t*.9+1)}px, ${1500 + 180*Math.cos(t*.4)}px)`;
  $('grid').style.transform = `perspective(900px) rotateX(55deg) translateY(${(t*120)%90}px) scale(2.2)`; $('grid').style.transformOrigin='50% 100%'; $('grid').style.opacity=.55;
  let flash = 0;
  for (const [i,a,b] of SC){
    const el = $('s'+i); if (t < a - .001 || t >= b){ el.style.opacity = 0; continue; }
    const pin = clamp((t-a)/.38,0,1), pout = clamp((t-(b-.24))/.24,0,1);
    const sIn = 1.28 - .28*ease(pin), sOut = 1 - .12*ease(pout);
    el.style.opacity = Math.min(ease(pin)*1.4, 1 - pout);
    el.style.transform = `scale(${sIn*sOut}) rotate(${(1-ease(pin))*(i%2?-3:3)}deg)`;
    el.style.filter = `blur(${(1-ease(pin))*16 + pout*12}px)`;
    flash = Math.max(flash, 1 - clamp((t-a)/.12,0,1));
    const lt = t - a, L = b - a;
    if (i===1){ const g=$('g1'); const j = (Math.sin(t*90)>.6)?1:0; g.style.textShadow = `${6+12*j}px 0 #FF3B8D, ${-6-12*j}px 0 #21E6C1`; g.style.transform = `translateX(${j*(Math.sin(t*300)*14)}px) skewX(${j*-6}deg)`; }
    if (i===2){ for (let q=0;q<3;q++){ const pp = spring(clamp((lt-.15-q*.12)/.5,0,1)); $('p'+q).style.transform = `translateY(${(1-pp)*900}px) rotate(${(q-1)*6*pp}deg) scale(${(1)})`; } const sp = spring(clamp((lt-.75)/.4,0,1)); $('st').style.transform = `scale(${.2+.8*sp}) rotate(${-8*sp}deg)`; $('st').style.opacity = clamp((lt-.7)/.15,0,1); }
    if (i===3){ for (let q=0;q<3;q++){ const pp = spring(clamp((lt-.2-q*.18)/.45,0,1)); const c=$('c'+q); c.style.transform = `translateX(-50%) scale(${pp})`; c.style.opacity = clamp((lt-.2-q*.18)/.1,0,1); c.querySelector('i').style.transform = `scaleX(${ease(clamp((lt-.75-q*.22)/.25,0,1))}) rotate(-4deg)`; } }
    if (i===4){ $('hh').style.transform = `rotate(${lt*240}deg)`; $('mh').style.transform = `rotate(${lt*1440}deg)`; }
    if (i===5){ $('f5').style.transform = `scale(${1.08 + .08*lt/L}) translateY(${-20*lt/L}%)`.replace('%)','px)'); }
    if (i===6){ for (let q=0;q<3;q++){ const pp = spring(clamp((lt-.15-q*.35)/.45,0,1)); const c=$('k'+q); c.style.transform = `translateX(${(1-pp)*-700}px)`; c.style.opacity = clamp((lt-.15-q*.35)/.15,0,1); } }
    if (i===7){ const pp = spring(clamp((lt-.3)/.5,0,1)); $('bt').style.transform = `translateX(-50%) scale(${(.6+.4*pp)*(1+.04*Math.sin(lt*7))})`; $('ar').style.transform = `translateY(${30*Math.abs(Math.sin(lt*5))}px)`; }
    if (i===8){ const sec = Math.max(0, 59 - Math.floor(lt*4)); $('cd').textContent = '23:59:' + String(sec).padStart(2,'0'); $('cd').style.color = (Math.floor(lt*4)%2)?'#FF3B5C':'#fff'; }
    if (i===9){ const pp = spring(clamp(lt/.45,0,1)); $('kl').style.transform = `scale(${(.5+.5*pp)*(1+.06*Math.sin(lt*9))})`; $('ar2').style.transform = `translateY(${36*Math.abs(Math.sin(lt*6))}px)`; }
  }
  $('flash').style.opacity = flash*.55;
}
window.setT = setT;
</script>
"""
    return B.page(w, h, V1_CSS, body).replace("</body>", TIMELINE_JS + js + "</body>")


def synth_music(out: Path, dur: float, hits: list):
    """Простой бит 120 BPM (бочка + хэт + бас) и вжухи на склейках. Всё синтез, без чужой музыки."""
    kick = "0.9*sin(2*PI*(48+120*exp(-28*mod(t,0.5)))*mod(t,0.5))*exp(-7*mod(t,0.5))"
    hat = "0.12*(random(0)*2-1)*exp(-45*mod(t+0.25,0.5))"
    bass = "0.22*sin(2*PI*55*t)*(0.6+0.4*sin(2*PI*2*t))*gt(mod(t,2),0.25)"
    pad = "0.06*(sin(2*PI*220*t)+sin(2*PI*277.18*t)+sin(2*PI*329.63*t))*(0.5+0.5*sin(2*PI*0.25*t))"
    srcs = [f"aevalsrc='{kick}+{hat}+{bass}+{pad}':s=44100:d={dur},highpass=f=30,afade=t=out:st={dur - 0.8}:d=0.8[m]"]
    labels = ["[m]"]
    for i, t in enumerate(hits):
        ms = int(t * 1000)
        srcs.append(f"anoisesrc=d=0.5:c=pink:a=0.3:r=44100,bandpass=f=1800:width_type=h:w=3000,afade=t=in:d=0.2,afade=t=out:st=0.2:d=0.3,adelay={ms}|{ms}[w{i}]")
        labels.append(f"[w{i}]")
    fc = ";".join(srcs) + ";" + "".join(labels) + f"amix=inputs={len(labels)}:normalize=0,atrim=0:{dur},volume=0.8[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-filter_complex", fc, "-map", "[out]", "-ac", "2", "-ar", "44100", str(out)], check=True)


# ---------------------------------------------------------------- I3-2 листаем сайт на фоне (нужен скрин сайта от Васи)

I32_CSS = """
body{background:#111}
#site{position:absolute;left:0;top:0;width:100%}
#site img{width:100%;display:block}
#ph{position:absolute;inset:0;background:repeating-linear-gradient(45deg,#2a2a2a 0 40px,#242424 40px 80px);display:flex;align-items:center;justify-content:center;color:#888;font:800 64px/1.2 Inter,sans-serif;text-align:center}
#shade{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(0,0,0,.55),rgba(0,0,0,.1) 45%,rgba(0,0,0,.65))}
.blk{position:absolute;left:60px;right:60px;text-align:center}
.blk span{display:inline;-webkit-box-decoration-break:clone;box-decoration-break:clone;padding:.1em .3em}
"""


def i32_html(f: dict, fmt: str) -> str:
    w, h = B.FORMATS[fmt]
    story = fmt == "story"
    shot = B.ASSETS / "site_fullpage.png"
    site = f'<div id="site"><img src="{B.uri(shot)}"></div>' if shot.exists() else '<div id="ph">SAYT<br>(Vasya yuboradi)</div>'
    top = 270 if story else 70
    body = (
        site + '<div id="shade"></div>'
        f'<div class="blk" id="t1" data-box data-maxh="{560 if story else 430}" style="top:{top}px;font:900 {70 if story else 60}px/1.18 Montserrat,sans-serif"><span style="background:#FFC21A;color:#111">{B.esc(f["headline"])}</span></div>'
        f'<div class="blk" id="t2" style="top:{(1110 if story else 820)}px;font:900 {84 if story else 70}px/1.1 Montserrat,sans-serif;text-transform:uppercase"><span style="background:#111;color:#fff">{B.esc(f["subline"])}</span></div>'
        f'<div class="blk" id="t3" style="top:{(1420 if story else 1050)}px;font:800 {44 if story else 38}px/1.2 Montserrat,sans-serif;text-transform:uppercase"><span style="background:#FFD95A;color:#111">{B.esc(f["cta"])} ⬇️</span></div>'
    )
    js = """
<script>
window.DURATION = 10.0;
function setT(t){
  const s = document.getElementById('site');
  if (s){ const H = s.offsetHeight - innerHeight; s.style.transform = `translateY(${-Math.max(0,H) * ease(clamp(t/9.5,0,1))}px)`; }
  [['t1',.3],['t2',3.0],['t3',4.2]].forEach(([id,a]) => { const e=document.getElementById(id); const p=spring(clamp((t-a)/.5,0,1)); e.style.opacity=clamp((t-a)/.2,0,1); e.style.transform=`translateY(${(1-p)*40}px)`; });
}
window.setT = setT;
</script>
"""
    return B.page(w, h, I32_CSS, body).replace("</body>", TIMELINE_JS + js + "</body>")


VIDEOS = {
    "V2": {"html": v2_html, "audio": [(1.0, "ding"), (3.0, "ding"), (5.0, "ding"), (7.0, "whoosh"), (8.6, "pop")], "dur": 12.0},
    "M2": {"html": m2_html, "audio": "scribble", "dur": None},
    "V1": {"html": v1_html, "audio": "music", "dur": 17.0},
    "I3-2": {"html": i32_html, "audio": [(0.3, "whoosh"), (3.0, "pop"), (4.2, "pop")], "dur": 10.0},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--only", default="V2")
    ap.add_argument("--fmt", default="story,feed")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--snap", default="")
    a = ap.parse_args()
    data = {c["id"]: c for c in json.loads((ROOT / ("creatives_uz.json" if a.lang == "uz" else "creatives_ru.json")).read_text(encoding="utf-8"))["creatives"]}
    key = "fields_uz" if a.lang == "uz" else "fields_ru"
    for vid in a.only.split(","):
        spec = VIDEOS[vid]
        f = dict(data[vid][key])
        f.update((data[vid].get("video_extra_" + a.lang) or {}))
        audio = OUT / a.lang / f"{vid}_audio.m4a"
        audio.parent.mkdir(parents=True, exist_ok=True)
        audio_fn = None
        if spec["audio"] == "scribble":
            audio_fn = lambda dur, write, _a=audio: synth_scribble(_a, write, dur)
        elif spec["audio"] == "music":
            synth_music(audio, spec["dur"], [1.8, 3.6, 5.6, 7.0, 9.6, 11.6, 13.6, 15.6])
        else:
            synth_audio(audio, spec["audio"], spec["dur"])
        for fmt in a.fmt.split(","):
            w, h = B.FORMATS[fmt]
            hp = B.OUT_HTML / f"{vid}_{fmt}_{a.lang}.html"
            hp.write_text(spec["html"](f, fmt), encoding="utf-8")
            if a.snap:
                asyncio.run(snap(hp, [float(x) for x in a.snap.split(",")], OUT / a.lang / "snaps", f"{vid}_{fmt}", w, h))
                continue
            asyncio.run(render_video(hp, OUT / a.lang / f"{vid}_{fmt}.mp4", w, h, audio, a.preview, audio_fn))


if __name__ == "__main__":
    main()
