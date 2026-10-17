import React from "react";
import { Easing, interpolate, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Manrope";

// Язык графики снят с референса (рил «Opus 5.5 vs original»):
// белый жирный гротеск, ключевое слово — синий градиент со свечением,
// плашка-чип с жёлтой полосой, стеклянные карточки, номера синим.
export const { fontFamily: FONT } = loadFont("normal", {
  weights: ["500", "600", "700", "800"],
  subsets: ["latin", "latin-ext"],
});

export const C = {
  bg: "#0B0910",
  white: "#FFFFFF",
  dim: "rgba(255,255,255,0.62)",
  blue1: "#2F55FF",
  blue2: "#7B96FF",
  yellow: "#F2C14E",
  green: "#3DDC84",
  red: "#FF3B5C",
  glass: "rgba(22,20,32,0.58)",
  glassBorder: "rgba(255,255,255,0.14)",
};

// Синий градиент светлее, чем в первой версии (аудит: контраст на сине-фиолетовом фоне был 2,6–3,7:1).
// paddingBottom/marginBottom — чтобы background-clip:text не срезал хвосты g, q, y.
export const BLUE_TEXT: React.CSSProperties = {
  backgroundImage: "linear-gradient(90deg, #5B7CFF, #A8B8FF)",
  WebkitBackgroundClip: "text",
  backgroundClip: "text",
  color: "transparent",
  paddingBottom: "0.25em",
  marginBottom: "-0.25em",
  paddingRight: "0.08em",
  filter: "drop-shadow(0 0 18px rgba(70,110,255,0.5)) drop-shadow(0 2px 6px rgba(0,0,0,0.55))",
};

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const EASE = Easing.bezier(0.22, 1, 0.36, 1);

// Появление элемента: прозрачность + подъём + размытие (как в референсе, 0.2–0.3 с).
export const enter = (frame: number, at: number, dur = 8, dy = 24) => {
  const p = interpolate(frame, [at, at + dur], [0, 1], { ...clamp, easing: EASE });
  return {
    opacity: p,
    translate: `0px ${(1 - p) * dy}px`,
    filter: `blur(${(1 - p) * 10}px)`,
  } as React.CSSProperties;
};

// Уход сцены: прозрачность + лёгкое уменьшение + размытие.
export const leave = (frame: number, end: number, dur = 7) => {
  // последний кадр сцены — end - 1 (аудит: иначе текст обрывался на 37% видимости)
  const p = interpolate(frame, [end - 1 - dur, end - 1], [0, 1], { ...clamp, easing: Easing.in(Easing.cubic) });
  return { opacity: 1 - p, scale: `${1 - p * 0.04}`, filter: `blur(${p * 12}px)` } as React.CSSProperties;
};

export const pop = (frame: number, at: number, dur = 10) => {
  const p = interpolate(frame, [at, at + dur], [0, 1], { ...clamp, easing: Easing.bezier(0.34, 1.56, 0.64, 1) });
  const o = interpolate(frame, [at, at + 4], [0, 1], clamp);
  return { opacity: o, scale: `${0.6 + 0.4 * p}`, filter: `blur(${(1 - Math.min(1, p)) * 14}px)` } as React.CSSProperties;
};

export const prog = (frame: number, a: number, b: number) => interpolate(frame, [a, b], [0, 1], { ...clamp, easing: EASE });

// Размеры зависят от формата: сторис 1080×1920 или лента 1080×1350.
export const useLayout = () => {
  const { width, height } = useVideoConfig();
  const feed = height < 1600;
  return { W: width, H: height, feed, k: feed ? 0.88 : 1, y: (story: number, feedY: number) => (feed ? feedY : story) };
};

export const Chip: React.FC<{ text: string; style?: React.CSSProperties; size?: number }> = ({ text, style, size = 34 }) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 14,
      padding: "10px 22px 10px 14px",
      background: "rgba(14,12,22,0.72)",
      border: `1px solid ${C.glassBorder}`,
      borderRadius: 10,
      color: C.white,
      fontFamily: FONT,
      fontWeight: 600,
      fontSize: size,
      letterSpacing: "0.02em",
      ...style,
    }}
  >
    <span style={{ width: 6, height: size * 1.15, borderRadius: 3, background: C.yellow, boxShadow: "0 0 14px rgba(242,193,78,.7)" }} />
    {text}
  </div>
);

export const Glass: React.FC<{ style?: React.CSSProperties; children?: React.ReactNode }> = ({ style, children }) => (
  <div
    style={{
      background: C.glass,
      border: `1px solid ${C.glassBorder}`,
      borderRadius: 26,
      backdropFilter: "blur(18px)",
      WebkitBackdropFilter: "blur(18px)",
      boxShadow: "0 30px 80px rgba(0,0,0,0.45)",
      ...style,
    }}
  >
    {children}
  </div>
);

// Субтитр референса: белая строка по словам (3 слова в секунду) + синее ключевое слово крупнее под ней.
export const Sub: React.FC<{ frame: number; at: number; end: number; line?: string; kw?: string; top: number; size?: number; kwSize?: number }> = ({ frame, at, end, line, kw, top, size = 52, kwSize = 74 }) => {
  const words = line ? line.split(" ") : [];
  const kwAt = at + words.length * 10 + (words.length ? 8 : 0);
  return (
    <div style={{ position: "absolute", left: 80, right: 80, top, textAlign: "center", fontFamily: FONT, zIndex: 20, ...(frame > end - 9 ? leave(frame, end) : {}) }}>
      {words.length ? (
        <div style={{ color: C.white, fontWeight: 800, fontSize: size, lineHeight: 1.15, textShadow: "0 3px 16px rgba(0,0,0,.6)" }}>
          {words.map((w, i) => (
            <span key={i} style={{ display: "inline-block", marginRight: "0.28em", ...enter(frame, at + i * 10, 6, 12) }}>{w}</span>
          ))}
        </div>
      ) : null}
      {kw ? <div style={{ ...BLUE_TEXT, fontWeight: 800, fontSize: kwSize, lineHeight: 1.1, marginTop: 4, ...enter(frame, kwAt, 7, 14) }}>{kw}</div> : null}
    </div>
  );
};
