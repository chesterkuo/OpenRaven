import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BlockLogo } from "../components/BlockLogo";
import { fontBody, fontChinese } from "../fonts";
import { colors, Locale } from "../styles";

type TurnSequenceProps = {
  locale?: Locale;
};

export const TurnSequence: React.FC<TurnSequenceProps> = ({ locale = "zh" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Background transitions from dark to warm cream
  const bgProgress = interpolate(frame, [0, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const r = interpolate(bgProgress, [0, 1], [26, 254]);
  const g = interpolate(bgProgress, [0, 1], [26, 249]);
  const b = interpolate(bgProgress, [0, 1], [26, 239]);
  const bgColor = `rgb(${r},${g},${b})`;

  // Text color transitions from white to dark
  const textR = interpolate(bgProgress, [0, 1], [255, 31]);
  const textG = interpolate(bgProgress, [0, 1], [255, 31]);
  const textB = interpolate(bgProgress, [0, 1], [255, 31]);
  const textColor = `rgb(${textR},${textG},${textB})`;

  const titleOpacity = spring({
    frame: frame - 50,
    fps,
    from: 0,
    to: 1,
    config: { damping: 20 },
  });

  const subtitleOpacity = spring({
    frame: frame - 70,
    fps,
    from: 0,
    to: 1,
    config: { damping: 20 },
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: bgColor,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 32,
      }}
    >
      <BlockLogo size={80} delay={20} />

      <div style={{ opacity: titleOpacity, textAlign: "center" }}>
        <div
          style={{
            fontFamily: locale === "zh" ? fontChinese : fontBody,
            fontSize: 56,
            fontWeight: 700,
            color: textColor,
          }}
        >
          {locale === "zh" ? "我們正在打造 OpenRaven。" : "We're building OpenRaven."}
        </div>
        <div
          style={{
            fontFamily: locale === "zh" ? fontBody : fontChinese,
            fontSize: 24,
            color: textColor,
            opacity: 0.6,
            marginTop: 8,
          }}
        >
          {locale === "zh" ? "We're building OpenRaven." : "我們正在打造 OpenRaven。"}
        </div>
      </div>

      <div style={{ opacity: subtitleOpacity, textAlign: "center" }}>
        <div
          style={{
            fontFamily: locale === "zh" ? fontChinese : fontBody,
            fontSize: 36,
            fontWeight: 500,
            color: colors.brand,
          }}
        >
          {locale === "zh" ? "一個 AI 知識編譯器" : "An AI knowledge compiler"}
        </div>
        <div
          style={{
            fontFamily: locale === "zh" ? fontBody : fontChinese,
            fontSize: 20,
            color: colors.brand,
            opacity: 0.7,
            marginTop: 4,
          }}
        >
          {locale === "zh" ? "An AI knowledge compiler" : "一個 AI 知識編譯器"}
        </div>
      </div>
    </AbsoluteFill>
  );
};
