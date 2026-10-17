import { Composition } from "remotion";
import { Montage } from "./montage/Montage";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition id="MontageStory" component={Montage} durationInFrames={990} fps={30} width={1080} height={1920} />
      <Composition id="MontageFeed" component={Montage} durationInFrames={990} fps={30} width={1080} height={1350} />
    </>
  );
};
