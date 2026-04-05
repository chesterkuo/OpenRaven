import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Caption } from "../components/Caption";
import { FadeIn } from "../components/FadeIn";
import { MiniGraph } from "../components/MiniGraph";
import { colors, Locale } from "../styles";

type GraphSequenceProps = {
  locale?: Locale;
};

export const GraphSequence: React.FC<GraphSequenceProps> = ({ locale = "zh" }) => {
  const frame = useCurrentFrame();

  // Slow zoom in
  const zoom = interpolate(frame, [0, 240], [1, 1.15], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.warmCream }}>
      {/* Caption at top */}
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          zIndex: 10,
        }}
      >
        <FadeIn delay={0}>
          <Caption
            zh="AI 自動萃取概念、建立連結、生成可查詢的知識庫"
            en="AI extracts concepts, builds connections, generates a queryable knowledge base"
            locale={locale}
            primarySize={38}
            subSize={18}
            color={colors.text}
          />
        </FadeIn>
      </div>

      {/* Graph */}
      <div
        style={{
          position: "absolute",
          top: 200,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          transform: `scale(${zoom})`,
          transformOrigin: "center center",
        }}
      >
        <MiniGraph width={1400} height={680} />
      </div>
    </AbsoluteFill>
  );
};
