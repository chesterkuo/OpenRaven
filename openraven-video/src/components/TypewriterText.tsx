import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

type TypewriterTextProps = {
  text: string;
  startFrame?: number;
  speed?: number; // frames per character
  style?: React.CSSProperties;
};

export const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  startFrame = 0,
  speed = 2,
  style,
}) => {
  const frame = useCurrentFrame();
  const charsToShow = Math.floor(
    interpolate(frame - startFrame, [0, text.length * speed], [0, text.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );

  return <span style={style}>{text.slice(0, charsToShow)}</span>;
};
