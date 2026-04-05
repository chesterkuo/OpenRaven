import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { fontBody, fontChinese } from "../fonts";
import { colors, Locale } from "../styles";

type TrustBadgeProps = {
  icon: React.ReactNode;
  zh: string;
  en: string;
  delay?: number;
  locale?: Locale;
};

export const TrustBadge: React.FC<TrustBadgeProps> = ({ icon, zh, en, delay = 0, locale = "zh" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: frame - delay,
    fps,
    from: 0,
    to: 1,
    config: { damping: 12, stiffness: 80 },
  });

  const translateY = (1 - progress) * 60;

  const primary = locale === "zh" ? zh : en;
  const sub = locale === "zh" ? en : zh;
  const primaryFont = locale === "zh" ? fontChinese : fontBody;
  const subFont = locale === "zh" ? fontBody : fontChinese;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 16,
        opacity: progress,
        transform: `translateY(${translateY}px)`,
        width: 280,
      }}
    >
      <div style={{ fontSize: 64, lineHeight: 1 }}>{icon}</div>
      <div
        style={{
          fontFamily: primaryFont,
          fontSize: 28,
          fontWeight: 700,
          color: colors.text,
        }}
      >
        {primary}
      </div>
      <div
        style={{
          fontFamily: subFont,
          fontSize: 18,
          color: colors.textMuted,
        }}
      >
        {sub}
      </div>
    </div>
  );
};
