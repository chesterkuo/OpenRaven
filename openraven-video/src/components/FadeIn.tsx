import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

type FadeInProps = {
  delay?: number;
  direction?: "up" | "down" | "none";
  distance?: number;
  children: React.ReactNode;
};

export const FadeIn: React.FC<FadeInProps> = ({
  delay = 0,
  direction = "up",
  distance = 30,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = spring({
    frame: frame - delay,
    fps,
    from: 0,
    to: 1,
    config: { damping: 20, stiffness: 80 },
  });

  const translateY =
    direction === "none"
      ? 0
      : interpolate(opacity, [0, 1], [direction === "up" ? distance : -distance, 0]);

  return (
    <div style={{ opacity, transform: `translateY(${translateY}px)` }}>
      {children}
    </div>
  );
};
