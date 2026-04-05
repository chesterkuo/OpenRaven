import React from "react";
import { Composition } from "remotion";
import { AbsoluteFill } from "remotion";

const Placeholder: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: "#1a1a1a", color: "#fff", display: "flex", justifyContent: "center", alignItems: "center", fontSize: 48 }}>
    OpenRaven Video
  </AbsoluteFill>
);

export const Root: React.FC = () => {
  return (
    <Composition
      id="Video"
      component={Placeholder}
      durationInFrames={1650}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
