import React from "react";
import { Composition } from "remotion";
import { TOTAL_FRAMES } from "./styles";
import { Video } from "./Video";

export const Root: React.FC = () => {
  return (
    <Composition
      id="Video"
      component={Video}
      durationInFrames={TOTAL_FRAMES}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
