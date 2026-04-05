import React from "react";
import { fontBody, fontChinese } from "../fonts";
import { Locale } from "../styles";

type CaptionProps = {
  zh: string;
  en: string;
  locale?: Locale;
  primarySize?: number;
  subSize?: number;
  color?: string;
  align?: "center" | "left";
};

export const Caption: React.FC<CaptionProps> = ({
  zh,
  en,
  locale = "zh",
  primarySize = 48,
  subSize = 22,
  color = "#ffffff",
  align = "center",
}) => {
  const primary = locale === "zh" ? zh : en;
  const sub = locale === "zh" ? en : zh;
  const primaryFont = locale === "zh" ? fontChinese : fontBody;
  const subFont = locale === "zh" ? fontBody : fontChinese;

  return (
    <div style={{ textAlign: align, maxWidth: 1400 }}>
      <div
        style={{
          fontFamily: primaryFont,
          fontSize: primarySize,
          fontWeight: 700,
          color,
          lineHeight: 1.4,
          marginBottom: 16,
        }}
      >
        {primary}
      </div>
      <div
        style={{
          fontFamily: subFont,
          fontSize: subSize,
          fontWeight: 400,
          color,
          opacity: 0.7,
          lineHeight: 1.5,
        }}
      >
        {sub}
      </div>
    </div>
  );
};
