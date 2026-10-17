import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useVideoConfig } from "remotion";
import { RoomBg } from "./Bg";
import { CardsScene, HookScene, ListScene, TimelineScene } from "./ScenesA";
import { ChecklistScene, CounterScene, CtaScene, WallScene } from "./ScenesB";

// Монтаж-ролик в стиле референса (без говорящей головы). 30 fps, 33 с. Тайминги после аудита (out/АУДИТ.md).
export const SCENES = [
  { name: "1 Хук: AI yaratdi", from: 0, dur: 75, C: HookScene },
  { name: "2 Карточки $100", from: 75, dur: 105, C: CardsScene },
  { name: "3 Список: bilmasdan", from: 180, dur: 120, C: ListScene },
  { name: "4 Таймлайн: ikki soatcha", from: 300, dur: 105, C: TimelineScene },
  { name: "5 Счётчик $1000", from: 405, dur: 150, C: CounterScene },
  { name: "6 Чек-лист", from: 555, dur: 90, C: ChecklistScene },
  { name: "7 Стена BEPUL", from: 645, dur: 150, C: WallScene },
  { name: "8 Призыв: Bosing", from: 795, dur: 195, C: CtaScene },
] as const;

export const MONTAGE_FRAMES = 990;

export const Montage: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: "#0B0910" }}>
      <RoomBg />
      {SCENES.map(({ name, from, dur, C }, i) => {
        // +4 кадра нахлёста: уход сцены перекрывает появление следующей, без пустых кадров на склейке (аудит п. 15)
        const d = i === SCENES.length - 1 ? dur : dur + 4;
        return (
          <Sequence key={name} name={name} from={from} durationInFrames={d} premountFor={fps}>
            <C dur={d} />
          </Sequence>
        );
      })}
      <Audio src={staticFile("montage_audio.m4a")} />
    </AbsoluteFill>
  );
};
