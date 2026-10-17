import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { BLUE_TEXT, C, Chip, FONT, Glass, enter, leave, pop, prog, useLayout } from "./ui";
import { T } from "./text";

type SceneProps = { dur: number };
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// 5. Карточка-график со счётчиком — грамматика «+1733 → +10 000 подписчиков» (референс 18–22 с).
export const CounterScene: React.FC<SceneProps> = ({ dur }) => {
  const f = useCurrentFrame();
  const L = useLayout();
  const ease = Easing.bezier(0.33, 0, 0.2, 1);
  const draw = interpolate(f, [10, 85], [0, 1], { ...clamp, easing: ease });
  const v = Math.round((100 + 900 * draw) / 10) * 10;
  const top = L.y(300, 100);
  const cw = 900;
  const chH = 300 * L.k;
  const pts = Array.from({ length: 11 }, (_, i) => [i / 10, 0.92 - 0.82 * Math.pow(i / 10, 1.35) + 0.04 * Math.sin(i * 2.1)]);
  const path = pts.map(([x, y], i) => `${i ? "L" : "M"} ${x * 800} ${y * chH}`).join(" ");
  const end = pts[pts.length - 1];
  return (
    <AbsoluteFill style={{ fontFamily: FONT, ...leave(f, dur) }}>
      <Glass style={{ position: "absolute", left: (L.W - cw) / 2, width: cw, top, height: 560 * L.k, padding: "30px 50px", ...enter(f, 2, 9, 40) }}>
        <div style={{ color: "rgba(255,255,255,.85)", fontSize: 40, fontWeight: 600 }}>{T.calcLabel}</div>
        <div style={{ ...BLUE_TEXT, fontWeight: 800, fontSize: 150 * L.k, lineHeight: 1.05, letterSpacing: "-0.02em" }}>{`$${v}`}</div>
        <svg width={800} height={chH} style={{ position: "absolute", left: 50, bottom: 40 * L.k, overflow: "visible" }}>
          {[0.25, 0.5, 0.75].map((y) => (
            <line key={y} x1={0} x2={800} y1={y * chH} y2={y * chH} stroke="rgba(255,255,255,.08)" strokeWidth={2} />
          ))}
          <path d={path} fill="none" stroke={C.blue2} strokeWidth={7} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} style={{ filter: "drop-shadow(0 0 10px rgba(123,150,255,.8))" }} />
          <circle cx={end[0] * 800} cy={end[1] * chH} r={14} fill="#fff" opacity={prog(f, 82, 86)} style={{ filter: "drop-shadow(0 0 14px #7B96FF)" }} />
        </svg>
        <div style={{ position: "absolute", right: 40, top: 34, ...pop(f, 85) }}>
          <span style={{ display: "inline-block", padding: "10px 18px", borderRadius: 999, background: "rgba(242,193,78,.16)", border: "1px solid rgba(242,193,78,.5)", color: C.yellow, fontWeight: 800, fontSize: 40 }}>{T.calcChip}</span>
        </div>
      </Glass>
      <div style={{ position: "absolute", left: 80, right: 80, top: top + 590 * L.k, textAlign: "center", ...enter(f, 20) }}>
        <div style={{ color: C.white, fontWeight: 800, fontSize: 52 * L.k, lineHeight: 1.15 }}>{T.qLine}</div>
        <div style={{ ...BLUE_TEXT, fontWeight: 800, fontSize: 72 * L.k, lineHeight: 1.1, marginTop: 8 }}>{T.qKw}</div>
      </div>
    </AbsoluteFill>
  );
};

// 6. Чек-лист — тот же язык, что список «ТОП-5», но с галочками.
export const ChecklistScene: React.FC<SceneProps> = ({ dur }) => {
  const f = useCurrentFrame();
  const L = useLayout();
  const top = L.y(560, 380);
  return (
    <AbsoluteFill style={{ fontFamily: FONT, ...leave(f, dur) }}>
      <AbsoluteFill style={{ background: "linear-gradient(90deg, rgba(6,5,10,.9) 0%, rgba(6,5,10,.6) 70%, rgba(6,5,10,0) 100%)", ...enter(f, 0, 8, 0) }} />
      <div style={{ position: "absolute", left: 80, right: 60, top: top - 220 * L.k, fontWeight: 800, fontSize: 76 * L.k, lineHeight: 1.05, ...enter(f, 0) }}>
        <span style={{ ...BLUE_TEXT }}>{T.bulletsChip.split(" ")[0]}</span> <span style={{ color: C.white }}>{T.bulletsChip.split(" ").slice(1).join(" ")}</span>
      </div>
      <div style={{ position: "absolute", left: 80, right: 60, top, display: "flex", flexDirection: "column", gap: 54 * L.k }}>
        {T.bullets.map((b, i) => {
          const at = 10 + i * 12;
          return (
            <div key={b} style={{ display: "flex", alignItems: "center", gap: 40, ...enter(f, at) }}>
              <span style={{ flex: "none", width: 108 * L.k, height: 108 * L.k, borderRadius: 26, background: `linear-gradient(135deg, ${C.blue1}, ${C.blue2})`, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 64 * L.k, fontWeight: 800, boxShadow: "0 0 30px rgba(70,110,255,.55)", ...pop(f, at + 2, 9) }}>✓</span>
              <span style={{ color: C.white, fontWeight: 800, fontSize: 72 * L.k, lineHeight: 1.05 }}>{b}</span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// 7. Стена из одного слова в 12 стилях — грамматика «ТОП-15 · СУБТИТРЫ» (референс 26–28 с).
const tileStyle = (i: number): React.CSSProperties => {
  const base: React.CSSProperties = { fontFamily: FONT, fontWeight: 800, fontSize: 52, lineHeight: 1, color: "#fff" };
  switch (i) {
    case 1: return { ...base, ...BLUE_TEXT };
    case 2: return { ...base, color: "#111", background: C.yellow, padding: "4px 10px", rotate: "-4deg" };
    case 3: return { ...base, color: "transparent", WebkitTextStroke: "2px #fff" };
    case 4: return { ...base, color: "#FF4FD8", textShadow: "0 0 12px #FF4FD8, 0 0 30px #FF4FD8" };
    case 5: return { ...base, letterSpacing: "0.35em", fontSize: 34, fontWeight: 600 };
    case 6: return { ...base, background: C.blue1, padding: "6px 12px", borderRadius: 8 };
    case 7: return { ...base, backgroundImage: "linear-gradient(90deg,#FF7A2F,#FF3B8D)", WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent" };
    case 8: return { ...base, textShadow: "3px 0 #FF3B5C, -3px 0 #21E6C1" };
    case 9: return { ...base, rotate: "-8deg", fontStyle: "italic" };
    case 10: return { ...base, color: "#21E6C1" };
    case 11: return { ...base, textShadow: "0 6px 0 #2F55FF, 0 12px 0 rgba(47,85,255,.5)" };
    default: return base;
  }
};

export const WallScene: React.FC<SceneProps> = ({ dur }) => {
  const f = useCurrentFrame();
  const L = useLayout();
  const top = L.y(380, 200);
  const cols = 3;
  const tw = 300;
  const th = 120 * L.k;
  return (
    <AbsoluteFill style={{ fontFamily: FONT, ...leave(f, dur) }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: top - 100 * L.k, textAlign: "center", ...enter(f, 1) }}>
        <Chip text={`${T.wallChip.toUpperCase()} · ${T.wallWord}`} size={42} />
      </div>
      {Array.from({ length: 12 }, (_, i) => {
        const r = Math.floor(i / cols);
        const c = i % cols;
        const at = 1 + i * 2.2;
        return (
          <Glass key={i} style={{ position: "absolute", left: 60 + c * (tw + 30), top: top + r * (th + 22), width: tw, height: th, borderRadius: 18, display: "flex", alignItems: "center", justifyContent: "center", ...pop(f, at, 8) }}>
            <span style={{ position: "absolute", left: 12, top: 8, color: C.dim, fontSize: 18, fontWeight: 600 }}>{String(i + 1).padStart(2, "0")}</span>
            {i === 0 ? (
              <span style={{ ...tileStyle(0), display: "inline-flex", alignItems: "center" }}>
                {T.wallWord.slice(0, Math.min(T.wallWord.length, Math.max(1, Math.round((f - at) / 2))))}
                <span style={{ display: "inline-block", width: 4, height: 44, marginLeft: 6, background: C.yellow, opacity: Math.round((f - at) / 2) >= T.wallWord.length ? 0 : Math.floor(f / 8) % 2 }} />
              </span>
            ) : (
              <span style={tileStyle(i)}>{T.wallWord}</span>
            )}
          </Glass>
        );
      })}
      <div style={{ position: "absolute", right: 80, top: top + 4 * (th + 22) + 16 * L.k, textAlign: "right", ...pop(f, 36) }}>
        <div style={{ ...BLUE_TEXT, fontWeight: 800, fontSize: 120 * L.k, lineHeight: 1 }}>{T.priceNew}</div>
      </div>
      <div style={{ position: "absolute", right: 80, left: 80, top: top + 4 * (th + 22) + 170 * L.k, textAlign: "right", fontWeight: 800, fontSize: 60 * L.k, ...enter(f, 54, 8, 14) }}>
        <span style={{ ...BLUE_TEXT }}>{T.wallKw}</span>
      </div>
    </AbsoluteFill>
  );
};

// 8. Призыв — грамматика «пиши МОНТАЖ» (референс 29–33 с), но механика «нажми кнопку под видео»:
// заголовок в 2 строки → карточка курса → строка с кнопкой «Bepul ko‘rish», кнопка «нажимается» → «BOSING» до последнего кадра.
export const CtaScene: React.FC<SceneProps> = ({ dur }) => {
  const f = useCurrentFrame();
  const L = useLayout();
  const out = prog(f, 138, 150);
  const fade = (st: React.CSSProperties): React.CSSProperties => ({ ...st, opacity: Number(st.opacity ?? 1) * (1 - out) });
  const press = interpolate(f, [75, 79, 83], [1, 0.9, 1], clamp);
  const ring = prog(f, 75, 95);
  const fin = prog(f, 144, 156);
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 60, right: 60, top: L.y(300, 150), textAlign: "center", ...fade(enter(f, 0)) }}>
        <div style={{ color: C.white, fontWeight: 800, fontSize: 72 * L.k, lineHeight: 1.08 }}>{T.ctaLine}</div>
        <div style={{ ...BLUE_TEXT, fontWeight: 800, fontSize: 72 * L.k, lineHeight: 1.08, marginTop: 6 }}>{T.ctaKw}</div>
      </div>
      <Glass style={{ position: "absolute", left: 80, right: 80, top: L.y(560, 390), height: 200 * L.k, display: "flex", alignItems: "center", gap: 34, padding: "0 36px", ...fade(enter(f, 45, 9, 40)) }}>
        <div style={{ flex: "none", width: 128 * L.k, height: 128 * L.k, borderRadius: 28, background: "linear-gradient(135deg, #5B7CFF, #A8B8FF)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ width: 0, height: 0, marginLeft: 10, borderLeft: "42px solid #fff", borderTop: "26px solid transparent", borderBottom: "26px solid transparent" }} />
        </div>
        <div>
          <div style={{ color: C.white, fontWeight: 800, fontSize: 54 * L.k }}>{T.cardTitle}</div>
          <div style={{ color: "rgba(255,255,255,.8)", fontWeight: 600, fontSize: 40 * L.k, marginTop: 6 }}>{T.cardSub}</div>
        </div>
      </Glass>
      <div style={{ position: "absolute", left: 80, right: 80, top: L.y(830, 640), height: 124 * L.k, borderRadius: 999, background: "rgba(20,18,30,.78)", border: `1px solid ${C.glassBorder}`, display: "flex", alignItems: "center", gap: 24, padding: "0 16px 0 24px", ...fade(enter(f, 60, 8, 30)) }}>
        <div style={{ flex: 1, color: C.white, fontWeight: 800, fontSize: 52 * L.k }}>{T.button}</div>
        <div style={{ position: "relative", flex: "none", width: 132 * L.k, height: 92 * L.k, borderRadius: 999, background: "linear-gradient(90deg,#6E5BFF,#9B7BFF)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 50, fontWeight: 800, scale: `${press}` }}>
          ↓
          <div style={{ position: "absolute", inset: -10, borderRadius: 999, border: "4px solid rgba(155,123,255,.9)", opacity: ring > 0 && ring < 1 ? 1 - ring : 0, scale: `${1 + ring * 0.5}` }} />
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: L.y(640, 420), textAlign: "center", opacity: fin, scale: `${0.75 + 0.25 * fin}` }}>
        <div style={{ ...BLUE_TEXT, fontWeight: 800, fontSize: 230 * L.k, lineHeight: 1, textTransform: "uppercase" }}>{T.final}</div>
        <div style={{ fontSize: 170 * L.k, marginTop: 30, translate: `0px ${24 * Math.abs(Math.sin(f / 5))}px` }}>⬇️</div>
      </div>
    </AbsoluteFill>
  );
};
