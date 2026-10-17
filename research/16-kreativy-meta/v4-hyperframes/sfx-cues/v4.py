"""Звук V4 «Bu rolikni AI yaratdi». Все времена — из timeline.json проекта.

Запуск (движок sound-design из whaleyxbt/claude-motion, чистый stdlib):
    cd ~/.claude/motion-repos/whaleyxbt_claude-motion
    python3 -m sfx <проект>/sfx-cues/v4.py --timeline <проект>/timeline.json --out <проект>/assets/audio/v4_sfx.wav

Ля минор, 120 BPM: бочка в долю, тики в слабые доли, пэд Am7 → Fmaj7 → Cmaj7 → G6.
Один риcер и один импакт — на главный удар «0 so‘m» (22,75 с).
"""

import math
import random

from sfx.synth import SR, blip, chime, click, envelope, impact, pad, pop, riser, scratch, whoosh

TARGET_LUFS = -14.0
SEED = 11

AM7 = [110.0, 164.81, 196.0, 261.63]
FMAJ7 = [87.31, 130.81, 164.81, 220.0]
CMAJ7 = [130.81, 196.0, 246.94, 329.63]
G6 = [98.0, 146.83, 164.81, 246.94]
PENTA = [440.0, 523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.66, 1318.51, 1567.98]


def kick(dur=0.34):
    """Короткая бочка: синус с падением высоты, как impact, но в 3 раза короче."""
    out, ph = [], 0.0
    for k in range(int(dur * SR)):
        tt = k / SR
        ph += 2 * math.pi * (46 + 95 * math.exp(-tt / 0.028)) / SR
        out.append(math.tanh(1.4 * math.sin(ph) * math.exp(-tt / 0.16)))
    return out


def glitch_burst(mix, t, n=6, gain=0.12):
    """Цифровой треск: серия щелчков с прыгающей высотой (детерминированно от seed)."""
    rng = random.Random(int(t * 1000))
    for k in range(n):
        mix.put(t + k / 30, click(rng.choice([900, 1400, 2600, 4200, 6000]), dur=0.03), gain, rng.uniform(-0.6, 0.6))


def bed(mix, tl):
    dur, w, hero = tl["duration"], tl["wall"], tl["s7"]["zero"]
    chords = [(0, AM7), (4, FMAJ7), (8, CMAJ7), (12, G6), (16, AM7), (20, FMAJ7), (24, G6), (w["swap"], CMAJ7)]
    volume = envelope([(0, 0.6), (0.4, 1), (w["flash"], 1), (w["swap"], 0.5), (w["swap"] + 1.2, 1), (dur - 1.0, 1), (dur, 0)])
    mix.put_stereo(0, *pad(dur, chords, volume=volume), gain=0.03)
    beat = tl["beat"]
    t = 0.0
    while t < w["start"] - 1e-6:  # прямая бочка до флёрри; вокруг главного удара — тишина бита
        if not hero - 0.75 <= t < hero + 0.5:
            mix.put(t, kick(), 0.42)
            mix.put(t + beat / 2, click(7800, dur=0.025), 0.05, 0.25)
        t += beat
    t = w["start"]
    while t < w["swap"] - 1e-6:  # в стене — восьмыми, разгон
        mix.put(t, kick(), 0.38)
        t += beat / 2
    t = tl["s8"]["start"]
    while t < dur - 0.6:  # призыв — половинный размер, спокойнее (сетка картинки, не момент пересвета)
        mix.put(t, kick(), 0.3)
        mix.put(t + beat, click(7800, dur=0.025), 0.04, -0.25)
        t += 2 * beat


def transitions(mix, tl):
    for T in (tl["s3"]["start"], tl["s4"]["start"], tl["s5"]["start"], tl["s6"]["start"]):  # zoom-through
        mix.put(T - 0.08, whoosh(0.55, 350, 3600, peak=0.55), 0.2)
    for T in (tl["s2"]["start"], tl["s7"]["start"]):  # glitch cut
        glitch_burst(mix, T, n=6, gain=0.13)
        mix.put(T, whoosh(0.3, 2500, 600, peak=0.3), 0.12)


def scene1(mix, s):
    glitch_burst(mix, 0.0, n=8, gain=0.1)
    mix.put(s["ai"], pop(1800, 220, dur=0.22), 0.34)
    mix.put(s["ai"], kick(0.5), 0.5)
    glitch_burst(mix, s["ai"], n=5, gain=0.1)
    mix.put(s["yar"] - 0.05, whoosh(0.35, 3200, 900, peak=0.35), 0.16, 0.4)
    mix.put(s["dot"], blip(1318.51, dur=0.35, tau=0.08), 0.14)
    glitch_burst(mix, s["glitch"], n=7, gain=0.11)


def scene2(mix, s):
    mix.put(s["cards"], whoosh(0.6, 400, 2400, peak=0.45), 0.16)
    n = s["cardCount"]
    for k in range(n):
        mix.put(s["cards"] + k * s["cardStep"] + 0.1, click(1600 + k * 140, dur=0.03), 0.08, -0.6 + k * 1.2 / (n - 1))
    for i, t in enumerate(s["words"]):
        mix.put(t, click(3200, dur=0.02), 0.035)
    for i in range(n):
        t = s["tags"] + i * s["tagStep"]
        pan = -0.6 + i * 1.2 / (n - 1)
        mix.put(t, pop(900 + i * 120, 420 + i * 55), 0.28, pan)
        mix.put(t + 0.005, blip(PENTA[1 + i], dur=0.3, tau=0.08), 0.08, pan)
    mix.put(s["dot"], blip(1318.51, dur=0.35, tau=0.08), 0.12)
    mix.put(s["shine"], whoosh(0.7, 2000, 7000, peak=0.5, q=0.5), 0.07)


def scene3(mix, s):
    for t in s["head"]:
        mix.put(t, click(3200, dur=0.02), 0.03)
    mix.put(s["kw1"], pop(1500, 200, dur=0.2), 0.28)
    mix.put(s["kw2"], whoosh(0.3, 3000, 900, peak=0.3), 0.14, -0.3)
    mix.put(s["dot"], blip(1318.51, dur=0.35, tau=0.08), 0.12)
    for i, t in enumerate(s["rows"]):
        mix.put(t, blip(PENTA[i], dur=0.25, tau=0.06), 0.1, -0.2 + i * 0.2)
        mix.put(t + s["strike"], scratch(0.3), 0.16, 0.2)
    mix.put(s["bloom"], chime([659.25, 880.0, 1318.51], dur=1.2, tau=0.5), 0.07)


def scene4(mix, s):
    for t in s["title"]:
        mix.put(t, click(3200, dur=0.02), 0.03)
    mix.put(s["kw"], pop(1400, 260, dur=0.2), 0.26)
    t = s["clock"]
    while t < s["clockEnd"]:  # часы крутятся — тикают шестнадцатыми
        mix.put(t, click(2600, dur=0.02), 0.05, 0.6)
        t += 0.125
    mix.put(s["panel"], whoosh(0.5, 300, 1800, peak=0.5), 0.12)
    for i in range(12):
        mix.put(s["thumbs"] + i * s["thumbStep"], click(1200 + i * 90, dur=0.025), 0.05, -0.6 + i * 0.1)
    names = (
        lambda t: mix.put(t, whoosh(0.35, 600, 3500, peak=0.5), 0.18, -0.4),
        lambda t: mix.put(t, pop(1100, 500), 0.28, 0.1),
        lambda t: mix.put(t, riser(0.24, 400, 3000), 0.12, 0.3),
        lambda t: glitch_burst(mix, t, n=4, gain=0.1),
        lambda t: mix.put(t, whoosh(0.3, 3800, 500, peak=0.3), 0.16, -0.1),
    )
    for play, t in zip(names, s["sfx"]):  # каждая плашка звучит своим звуком
        play(t)


def scene5(mix, s):
    mix.put(s["card"], whoosh(0.5, 300, 2000, peak=0.5), 0.12)
    for i in range(s["steps"]):  # $100 → $1000 — десять нот вверх
        mix.put(s["count0"] + i * s["stepGap"], blip(PENTA[i], dur=0.3, tau=0.07), 0.13, -0.4 + i * 0.09)
    land = s["count0"] + (s["steps"] - 1) * s["stepGap"]
    mix.put(land + 0.02, chime([880.0, 1318.51, 1760.0], dur=1.4, tau=0.5), 0.12)
    for i in range(6):
        mix.put(s["q1"] + i * s["q1Step"], click(3200, dur=0.02), 0.03)
    mix.put(s["q2"], pop(1600, 240, dur=0.2), 0.26)
    mix.put(s["chip"], pop(1200, 600), 0.2, 0.5)


def scene6(mix, s):
    mix.put(s["bepul"], pop(1500, 200, dur=0.2), 0.3)
    mix.put(s["mini"], whoosh(0.35, 2600, 800, peak=0.35), 0.14)
    mix.put(s["dot"], blip(1318.51, dur=0.35, tau=0.08), 0.12)
    for i, t in enumerate(s["items"]):
        mix.put(t, pop(900 + i * 200, 450 + i * 90), 0.26, -0.2 + i * 0.2)
        mix.put(t + 0.12, blip(PENTA[4 + i], dur=0.45, tau=0.12), 0.1)
    mix.put(s["items"][-1] + 0.3, chime([523.25, 783.99, 1046.5], dur=1.3, tau=0.5), 0.08)


def scene7(mix, s):
    mix.put(s["chip"], pop(700, 360), 0.14)
    for i in range(12):
        mix.put(s["tiles"] + i * s["tileStep"], click(1300 + i * 120, dur=0.03), 0.09, -0.6 + (i % 3) * 0.6)
    mix.put(s["riser"], riser(s["zero"] - s["riser"]), 0.2)
    mix.put(s["zero"] - 0.01, impact(), 0.55)
    mix.put(s["zero"], chime([440.0, 659.25, 880.0, 1318.51], dur=2.0, tau=0.8), 0.12)
    mix.put(s["later"], pop(800, 380), 0.18)
    for i in range(12):
        mix.put(s["wave"] + (i % 3) * 0.06 + (i // 3) * 0.08, click(5200, dur=0.02), 0.025, -0.5 + (i % 3) * 0.5)


def wall(mix, w):
    mix.put(w["start"], whoosh(0.5, 300, 2600, peak=0.4), 0.22)
    mix.put(w["cardOut"], whoosh(0.4, 900, 4200, peak=0.6), 0.2, 0.3)
    mix.put(w["invert"], click(1800, dur=0.04), 0.2)
    mix.put(w["invert"], blip(1046.5, dur=0.3, tau=0.07), 0.1)
    mix.put(w["speed"], whoosh(w["swap"] - w["speed"] + 0.05, 500, 6000, peak=0.9, q=0.6), 0.26)
    mix.put(w["swap"], whoosh(0.8, 6000, 300, peak=0.1, q=0.6), 0.16)
    mix.put(w["swap"], chime([523.25, 659.25, 783.99, 1046.5], dur=1.6, tau=0.6), 0.1)


def scene8(mix, s):
    for t in s["l1"] + s["l2"]:
        mix.put(t, click(3200, dur=0.02), 0.035)
    mix.put(s["card"], pop(900, 450), 0.2, -0.3)
    mix.put(s["final"], pop(1500, 220, dur=0.22), 0.3)
    mix.put(s["final"], kick(0.5), 0.36)
    mix.put(s["final"] + 0.05, chime([523.25, 659.25, 783.99, 1046.5, 1318.51], dur=2.2, tau=0.9), 0.14)
    for i in range(3):  # шевроны вниз — к настоящей кнопке под видео
        mix.put(s["chev"] + i * 0.08, blip(PENTA[6 - i * 2], dur=0.25, tau=0.06), 0.09, 0.0)


def score(mix, tl):
    bed(mix, tl)
    transitions(mix, tl)
    scene1(mix, tl["s1"])
    scene2(mix, tl["s2"])
    scene3(mix, tl["s3"])
    scene4(mix, tl["s4"])
    scene5(mix, tl["s5"])
    scene6(mix, tl["s6"])
    scene7(mix, tl["s7"])
    wall(mix, tl["wall"])
    scene8(mix, tl["s8"])
