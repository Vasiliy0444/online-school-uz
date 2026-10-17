"""Звук для монтажа: бит 120 BPM + вжухи на сменах сцен + щелчки на появлении элементов.
Всё синтезируется ffmpeg — без чужой музыки. Тайминги совпадают с SCENES в src/montage/Montage.tsx.

python3 make_audio.py  → public/montage_audio.m4a
"""
import subprocess
from pathlib import Path

FPS = 30
DUR = 990 / FPS
OUT = Path(__file__).resolve().parent / "public" / "montage_audio.m4a"

SCENE_STARTS = [0, 75, 180, 300, 405, 555, 645, 795]


def t(frame: float) -> float:
    return frame / FPS


def events():
    s = dict(zip(["hook", "cards", "list", "time", "count", "check", "wall", "cta"], SCENE_STARTS))
    ev = [(t(v), "whoosh") for v in SCENE_STARTS[1:]]
    ev.append((t(12), "boom"))  # «AI yaratdi»
    ev += [(t(s["cards"] + 3 + i * 4), "pop") for i in range(5)]  # карточки
    ev += [(t(s["cards"] + 18 + i * 8), "tick") for i in range(5)]  # цены $100
    ev += [(t(s["list"] + 22 + i * 15), "pop") for i in range(3)]  # пункты
    ev += [(t(s["list"] + 30 + i * 15), "swish") for i in range(3)]  # зачёркивание
    ev += [(t(s["time"] + 14 + i * 9), "pop") for i in range(5)]  # клипы SFX
    ev += [(t(s["count"] + 10 + i * 5), "tick") for i in range(15)]  # счёт 10–85
    ev.append((t(s["count"] + 85), "pop"))
    ev += [(t(s["check"] + 12 + i * 12), "pop") for i in range(3)]  # галочки
    ev += [(t(s["wall"] + 1 + i * 2.2), "tick") for i in range(12)]  # плитки
    ev.append((t(s["wall"] + 36), "boom"))  # 0 so‘m
    ev.append((t(s["wall"] + 54), "pop"))  # Keyin — 3 mln so‘m
    ev.append((t(s["cta"] + 45), "pop"))  # карточка
    ev.append((t(s["cta"] + 75), "type"))  # нажатие кнопки
    ev.append((t(s["cta"] + 76), "pop"))
    ev.append((t(s["cta"] + 144), "boom"))  # BOSING
    return ev


SRC = {
    "whoosh": "anoisesrc=d=0.55:c=pink:a=0.32:r=44100,bandpass=f=1600:width_type=h:w=2600,afade=t=in:d=0.25,afade=t=out:st=0.25:d=0.3",
    "pop": "aevalsrc='0.55*sin(2*PI*(380+900*exp(-35*t))*t)*exp(-16*t)':s=44100:d=0.3",
    "tick": "aevalsrc='0.28*sin(2*PI*2400*t)*exp(-60*t)':s=44100:d=0.08",
    "type": "anoisesrc=d=0.05:c=white:a=0.25:r=44100,highpass=f=2500,afade=t=out:d=0.05",
    "swish": "anoisesrc=d=0.3:c=white:a=0.18:r=44100,bandpass=f=4000:width_type=h:w=3000,afade=t=in:d=0.1,afade=t=out:st=0.1:d=0.2",
    "boom": "aevalsrc='0.9*sin(2*PI*(42+90*exp(-14*t))*t)*exp(-4.5*t)':s=44100:d=0.9",
}


def main():
    kick = "0.75*sin(2*PI*(48+120*exp(-28*mod(t,0.5)))*mod(t,0.5))*exp(-7*mod(t,0.5))"
    hat = "0.09*(random(0)*2-1)*exp(-45*mod(t+0.25,0.5))"
    bass = "0.18*sin(2*PI*55*t)*(0.6+0.4*sin(2*PI*2*t))*gt(mod(t,2),0.25)"
    pad = "0.05*(sin(2*PI*220*t)+sin(2*PI*277.18*t)+sin(2*PI*329.63*t))*(0.5+0.5*sin(2*PI*0.25*t))"
    parts = [f"aevalsrc='{kick}+{hat}+{bass}+{pad}':s=44100:d={DUR:.3f},highpass=f=30,afade=t=in:d=0.4,afade=t=out:st={DUR - 1:.3f}:d=1[m]"]
    labels = ["[m]"]
    for i, (when, kind) in enumerate(events()):
        ms = int(when * 1000)
        parts.append(f"{SRC[kind]},adelay={ms}|{ms}[e{i}]")
        labels.append(f"[e{i}]")
    parts.insert(0, f"anullsrc=r=44100:cl=stereo:d={DUR:.3f}[base]")
    labels.insert(0, "[base]")
    fc = ";".join(parts) + ";" + "".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=first,alimiter=limit=0.9,volume=0.95[out]"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-filter_complex", fc, "-map", "[out]", "-ac", "2", "-ar", "44100", "-c:a", "aac", "-b:a", "192k", str(OUT)], check=True)
    print("audio", OUT, f"{DUR:.2f}s", len(labels) - 2, "events")


if __name__ == "__main__":
    main()
