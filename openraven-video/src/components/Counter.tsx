import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { fontBody } from "../fonts";

type CounterProps = {
  from?: number;
  to: number;
  startFrame: number;
  duration?: number;
  label: string;
  color?: string;
};

export const Counter: React.FC<CounterProps> = ({
  from = 0,
  to,
  startFrame,
  duration = 40,
  label,
  color = "#1f1f1f",
}) => {
  const frame = useCurrentFrame();
  const value = Math.round(
    interpolate(frame, [startFrame, startFrame + duration], [from, to], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );

  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontFamily: fontBody, fontSize: 48, fontWeight: 700, color }}>
        {value.toLocaleString()}
      </div>
      <div style={{ fontFamily: fontBody, fontSize: 18, color, opacity: 0.6, marginTop: 4 }}>
        {label}
      </div>
    </div>
  );
};
