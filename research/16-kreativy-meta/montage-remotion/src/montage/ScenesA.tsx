import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { BLUE_TEXT, C, Chip, FONT, Glass, Sub, enter, leave, pop, prog, useLayout } from "./ui";
import { T } from "./text";

type SceneProps = { dur: number };

// 1. Хук: текст по дуге слева + крупное слово справа (референс 0–3.5 с: «вы можете дальше» + «монтировать»).
export const HookScene: React.FC<SceneProps> = ({ dur }) => {
  const f = useCurrentFrame();
  const L = useLayout();
  const chars = Math.round(interpolate(f, [0, 18], [2, T.hookArc.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const arcTop = L.y(1180, 960);
  return (
    <AbsoluteFill style={{ fontFamily: FONT, ...leave(f, dur) }}>
      <svg width={L.W} height={L.H} style={{ position: "absolute", inset: 0 }}>
        <path id="arc" d={`M 175 ${arcTop} A 640 640 0 0 1 700 ${arcTop - 620}`} fill="none" />
        <text fill="#fff" fontFamily={FONT} fontWeight={800} fontSize={124 * L.k} style={{ filter: "drop-shadow(0 4px 18px rgba(0,0,0,.55))" }}>
          <textPath href="#arc" startOffset="2%">
            {T.hookArc.slice(0, chars)}
          </textPath>
        </text>
      </svg>
      <div style={{ position: "absolute", right: 80, top: L.y(600, 440), textAlign: "right", ...pop(f, 12, 10) }}>
        <div style={{ ...BLUE_TEXT, fontWeight: 800, fontSize: 210 * L.k, lineHeight: 0.95, letterSpacing: "-0.02em" }}>AI</div>
        <div style={{ color: C.white, fontWeight: 800, fontSize: 132 * L.k, lineHeight: 1, letterSpacing: "-0.02em", textShadow: "0 6px 30px rgba(0,0,0,.6)" }}>
          {T.hookPop.replace(/^AI\s*/, "")}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// Карточки «работ»: сайт — настоящий скриншот racescout.ai (public/site_phone.png), остальные — нарисованные макеты (рилс, бот, логотип).
const CardUI: React.FC<{ kind: number }> = ({ kind }) => {
  if (kind === 1)
    return (
      <div style={{ position: "absolute", inset: 0, background: "#111" }}>
        <Img src={staticFile("site_phone.png")} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top center" }} />
      </div>
    );
  if (kind === 2)
    return (
      <div style={{ position: "absolute", inset: 0, background: "#0E1621", padding: 14 }}>
        {[["#2B5278", "62%", 0], ["#182533", "70%", 1], ["#2B5278", "50%", 0], ["#182533", "78%", 1], ["#2B5278", "44%", 0]].map(([bg, w, side], i) => (
          <div key={i} style={{ marginTop: 14, marginLeft: side ? 0 : "auto", width: w as string, height: 34, borderRadius: 14, background: bg as string }} />
        ))}
        <div style={{ position: "absolute", left: 14, right: 14, bottom: 16, height: 40, borderRadius: 20, background: "#17212B", border: "1px solid #2b3a4a" }} />
      </div>
    );
  if (kind === 3)
    return (
      <div style={{ position: "absolute", inset: 0, background: "linear-gradient(160deg,#141414,#2a2a2a)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: 120, height: 120, borderRadius: 34, background: "conic-gradient(from 200deg,#F2C14E,#FF4E8A,#7A3BFF,#21E6C1,#F2C14E)", transform: "rotate(12deg)" }} />
      </div>
    );
  const grad = kind === 0 ? "linear-gradient(160deg,#FF4E8A,#7A3BFF)" : "linear-gradient(160deg,#21E6C1,#2F55FF)";
  return (
    <div style={{ position: "absolute", inset: 0, background: grad }}>
      <div style={{ position: "absolute", left: "50%", top: "42%", width: 0, height: 0, marginLeft: -20, marginTop: -30, borderLeft: "52px solid rgba(255,255,255,.92)", borderTop: "32px solid transparent", borderBottom: "32px solid transparent" }} />
      {[0.85, 0.6].map((w, i) => (
        <div key={i} style={{ position: "absolute", left: 16, bottom: 22 + i * 22, height: 12, width: `${w * 80}%`, borderRadius: 6, background: "rgba(255,255,255,.55)" }} />
      ))}
    </div>
  );
};

const CARD_LABELS = ["Reels", "Sayt", "Bot", "Logo", "Reels"];

// 2. Карточки работ с ценой — грамматика «залетевшие ролики + цифры охватов» (референс 13–16 с).
export const CardsScene: React.FC<SceneProps> = ({ dur }) => {
  const f = useCurrentFrame();
  const L = useLayout();
  const cy = L.y(700, 560);
  const xs = [170, 355, 540, 725, 910];
  const rot = [-14, -7, 0, 7, 14];
  const dy = [70, 22, 0, 22, 70];
  const cw = 230 * L.k;
  const ch = 410 * L.k;
  return (
    <AbsoluteFill style={{ fontFamily: FONT, ...leave(f, dur) }}>
      {xs.map((x, i) => {
        const at = 3 + i * 4;
        const p = prog(f, at, at + 12);
        const fl = 7 * Math.sin(f / 14 + i);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x - cw / 2,
              top: cy - ch / 2 + dy[i] + (1 - p) * 420 + fl,
              width: cw,
              height: ch,
              rotate: `${rot[i] * p}deg`,
              opacity: p,
              borderRadius: 26,
              overflow: "hidden",
              border: "3px solid rgba(255,255,255,.22)",
              boxShadow: "0 30px 60px rgba(0,0,0,.55)",
              zIndex: i === 2 ? 5 : 5 - Math.abs(i - 2),
            }}
          >
            <CardUI kind={i} />
            <div style={{ position: "absolute", left: 12, top: i === 1 ? 44 : 12, padding: "4px 12px", borderRadius: 999, background: "rgba(0,0,0,.45)", color: "#fff", fontWeight: 700, fontSize: 30 }}>{CARD_LABELS[i]}</div>
          </div>
        );
      })}
      {xs.map((x, i) => (
        <div
          key={`p${i}`}
          style={{
            position: "absolute",
            left: x - 110,
            width: 220,
            top: cy + ch / 2 + dy[i] - 20,
            textAlign: "center",
            fontStyle: "italic",
            fontWeight: 800,
            fontSize: 56 * L.k,
            rotate: `${rot[i] * 0.6}deg`,
            zIndex: 10,
            ...BLUE_TEXT,
            ...pop(f, 18 + i * 8, 10),
          }}
        >
          {T.price}
        </div>
      ))}
      <Sub frame={f} at={20} end={dur} line={T.cardsLine} kw={T.cardsKw} top={L.y(1030, 1010)} size={56} kwSize={80} />
    </AbsoluteFill>
  );
};

// 3. Список на тёмной подложке слева — грамматика «ТОП-5 принципов» (референс 6–10.6 с), пункты зачёркиваются.
export const ListScene: React.FC<SceneProps> = ({ dur }) => {
  const f = useCurrentFrame();
  const L = useLayout();
  const top = L.y(300, 150);
  return (
    <AbsoluteFill style={{ fontFamily: FONT, ...leave(f, dur) }}>
      <AbsoluteFill style={{ background: "linear-gradient(90deg, rgba(6,5,10,.94) 0%, rgba(6,5,10,.78) 58%, rgba(6,5,10,0) 100%)", ...enter(f, 0, 6, 0) }} />
      <div style={{ position: "absolute", left: 80, right: 120, top, ...enter(f, 0) }}>
        <div style={{ color: C.white, fontWeight: 800, fontSize: 76 * L.k, lineHeight: 1.08 }}>{T.listHead}</div>
        <div style={{ ...BLUE_TEXT, fontWeight: 800, fontSize: 90 * L.k, lineHeight: 1.05, textTransform: "uppercase", marginTop: 6 }}>{T.listKw}</div>
      </div>
      {T.chips.map((w, i) => {
        const at = 22 + i * 15;
        const s = prog(f, at + 8, at + 16);
        return (
          <div key={w} style={{ position: "absolute", left: 80, top: top + (430 + i * 150) * L.k, display: "flex", alignItems: "center", gap: 40, ...enter(f, at) }}>
            <span style={{ ...BLUE_TEXT, fontWeight: 800, fontSize: 92 * L.k, width: 140 * L.k }}>{`0${i + 1}`}</span>
            <span style={{ position: "relative", color: C.white, fontWeight: 700, fontSize: 82 * L.k }}>
              {w}
              <span style={{ position: "absolute", left: -10, top: "54%", height: 9, width: `calc((100% + 20px) * ${s})`, background: C.red, borderRadius: 5, rotate: "-3deg", boxShadow: "0 0 18px rgba(255,59,92,.6)" }} />
            </span>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// 4. Таймлайн монтажа, который «собирает сам» — грамматика «SFX-ЗВУКИ» (референс 23–25 с).
const wave = Array.from({ length: 64 }, (_, i) => 0.25 + 0.75 * Math.abs(Math.sin(i * 1.7) * Math.cos(i * 0.37)));
const SFX_COLORS = ["#FF5C8A", "#5C7CFF", "#F2C14E", "#B07CFF", "#3DDC84"];

export const TimelineScene: React.FC<SceneProps> = ({ dur }) => {
  const f = useCurrentFrame();
  const L = useLayout();
  const px = 60;
  const pw = L.W - 2 * px;
  const pTop = L.y(780, 680);
  const head = interpolate(f, [6, dur - 6], [0.04, 0.96], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ fontFamily: FONT, ...leave(f, dur) }}>
      <div style={{ position: "absolute", left: 80, right: 80, top: L.y(300, 130), ...enter(f, 0) }}>
        <div style={{ color: C.white, fontWeight: 800, fontSize: 92 * L.k, lineHeight: 1.05 }}>{T.timeLine}</div>
        <div style={{ ...BLUE_TEXT, fontWeight: 800, fontSize: 118 * L.k, lineHeight: 1.05 }}>{T.timeKw}</div>
      </div>
      <svg width={150 * L.k} height={150 * L.k} viewBox="0 0 100 100" style={{ position: "absolute", right: 80, top: L.y(330, 150), ...pop(f, 8) }}>
        <circle cx="50" cy="50" r="42" fill="none" stroke={C.blue2} strokeWidth="7" />
        <line x1="50" y1="50" x2="50" y2="22" stroke="#fff" strokeWidth="6" strokeLinecap="round" transform={`rotate(${f * 9} 50 50)`} />
        <line x1="50" y1="50" x2="70" y2="50" stroke={C.yellow} strokeWidth="6" strokeLinecap="round" transform={`rotate(${f * 1.2} 50 50)`} />
      </svg>
      <div style={{ position: "absolute", left: px + 10, top: pTop - 64, ...enter(f, 4) }}>
        <Chip text={T.timeChip} size={40} />
      </div>
      <Glass style={{ position: "absolute", left: px, width: pw, top: pTop, height: 440 * L.k, overflow: "hidden", ...enter(f, 5, 9, 40) }}>
        <div style={{ position: "absolute", left: 70, right: 20, top: 14, display: "flex", justifyContent: "space-between", color: C.dim, fontSize: 20, fontWeight: 600 }}>
          {["00:00", "00:05", "00:10", "00:15", "00:20", "00:25"].map((t) => (
            <span key={t}>{t}</span>
          ))}
        </div>
        {["V1", "A1", "SFX", "SFX"].map((tr, i) => (
          <div key={i} style={{ position: "absolute", left: 18, top: (66 + i * 98) * L.k, color: C.dim, fontSize: 20, fontWeight: 700 }}>{tr}</div>
        ))}
        <div style={{ position: "absolute", left: 70, right: 20, top: 56 * L.k, height: 70 * L.k, display: "flex", gap: 4 }}>
          {Array.from({ length: 14 }, (_, i) => (
            <div key={i} style={{ flex: 1, borderRadius: 6, background: `linear-gradient(160deg, hsl(${250 + i * 9},70%,${40 + (i % 3) * 8}%), hsl(${200 + i * 7},70%,30%))`, opacity: prog(f, 6 + i * 1.2, 10 + i * 1.2) }} />
          ))}
        </div>
        <div style={{ position: "absolute", left: 70, right: 20, top: 150 * L.k, height: 74 * L.k, display: "flex", alignItems: "center", gap: 3 }}>
          {wave.map((h, i) => (
            <div key={i} style={{ flex: 1, height: `${h * 100 * prog(f, 8 + i * 0.25, 14 + i * 0.25)}%`, borderRadius: 3, background: C.green }} />
          ))}
        </div>
        {T.sfx.map((name, i) => {
          const lane = i % 2;
          const x = 0.03 + i * 0.185;
          const at = 14 + i * 9;
          return (
            <div
              key={name}
              style={{
                position: "absolute",
                left: `calc(70px + (100% - 90px) * ${x})`,
                width: "16%",
                top: (250 + lane * 98) * L.k,
                height: 64 * L.k,
                borderRadius: 10,
                background: SFX_COLORS[i],
                color: "#111",
                fontWeight: 800,
                fontSize: 22,
                padding: "6px 10px",
                boxShadow: "0 8px 20px rgba(0,0,0,.35)",
                ...pop(f, at, 8),
              }}
            >
              {name}
            </div>
          );
        })}
        <div style={{ position: "absolute", top: 40, bottom: 10, left: `calc(70px + (100% - 90px) * ${head})`, width: 3, background: "#fff", boxShadow: "0 0 12px #fff" }}>
          <div style={{ position: "absolute", top: -6, left: -9, width: 21, height: 21, borderRadius: 11, background: "#fff" }} />
        </div>
      </Glass>
    </AbsoluteFill>
  );
};
