import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors } from "../styles";

type BlockLogoProps = {
  size?: number;
  delay?: number;
};

const BAR_COLORS = [colors.brandGold, colors.brandAmber, colors.brandFlame, colors.brand];

export const BlockLogo: React.FC<BlockLogoProps> = ({ size = 48, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ display: "flex", gap: size * 0.1 }}>
      {BAR_COLORS.map((color, i) => {
        const scale = spring({
          frame: frame - delay - i * 4,
          fps,
          from: 0,
          to: 1,
          config: { damping: 12, stiffness: 120 },
        });

        return (
          <div
            key={i}
            style={{
              width: size * 0.18,
              height: size,
              backgroundColor: color,
              borderRadius: size * 0.05,
              transform: `scaleY(${scale})`,
              transformOrigin: "bottom",
            }}
          />
        );
      })}
    </div>
  );
};
