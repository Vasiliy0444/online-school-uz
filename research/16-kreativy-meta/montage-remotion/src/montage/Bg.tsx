import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

// Фон вместо говорящей головы: тёмная комната с цветным светом мониторов,
// как в референсе (фиолетовый, тёплый оранжевый, голубой), плюс зерно и виньетка.
// Пятна медленно «дышат» — постоянное микродвижение, чтобы кадр не был мёртвым.
const blob = (x: number, y: number, size: number, color: string, opacity: number): React.CSSProperties => ({
  position: "absolute",
  left: x - size / 2,
  top: y - size / 2,
  width: size,
  height: size,
  borderRadius: "50%",
  background: color,
  opacity,
  filter: "blur(140px)",
});

export const RoomBg: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / 30;
  return (
    <AbsoluteFill style={{ background: "#0B0910", overflow: "hidden" }}>
      <div style={{ ...blob(260 + 60 * Math.sin(t * 0.35), 520 + 80 * Math.cos(t * 0.3), 900, "#7A3BFF", 0.28) }} />
      <div style={{ ...blob(900 + 50 * Math.cos(t * 0.28), 1250 + 70 * Math.sin(t * 0.33), 1000, "#FF7A2F", 0.3) }} />
      <div style={{ ...blob(820 + 40 * Math.sin(t * 0.4 + 1), 380 + 60 * Math.sin(t * 0.25), 700, "#2E6BFF", 0.22) }} />
      <div style={{ ...blob(200, 1650 + 50 * Math.cos(t * 0.31), 760, "#C2309B", 0.22) }} />
      {/* мягкие «мониторы» на заднем плане */}
      <div style={{ position: "absolute", left: 90, top: 760, width: 420, height: 250, borderRadius: 18, background: "rgba(120,170,255,0.10)", filter: "blur(18px)" }} />
      <div style={{ position: "absolute", left: 600, top: 700, width: 380, height: 230, borderRadius: 18, background: "rgba(90,200,255,0.09)", filter: "blur(18px)" }} />
      <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity: 0.16, mixBlendMode: "overlay" }}>
        <filter id="grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={f % 7} stitchTiles="stitch" />
        </filter>
        <rect width="100%" height="100%" filter="url(#grain)" />
      </svg>
      <AbsoluteFill style={{ background: "radial-gradient(120% 90% at 50% 45%, rgba(0,0,0,0) 40%, rgba(0,0,0,0.7) 100%)" }} />
    </AbsoluteFill>
  );
};
