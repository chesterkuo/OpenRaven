import React from "react";
import { fontBody, fontChinese } from "../fonts";

type CaptionProps = {
  zh: string;
  en: string;
  zhSize?: number;
  enSize?: number;
  color?: string;
  align?: "center" | "left";
};

export const Caption: React.FC<CaptionProps> = ({
  zh,
  en,
  zhSize = 48,
  enSize = 22,
  color = "#ffffff",
  align = "center",
}) => {
  return (
    <div style={{ textAlign: align, maxWidth: 1400 }}>
      <div
        style={{
          fontFamily: fontChinese,
          fontSize: zhSize,
          fontWeight: 700,
          color,
          lineHeight: 1.4,
          marginBottom: 16,
        }}
      >
        {zh}
      </div>
      <div
        style={{
          fontFamily: fontBody,
          fontSize: enSize,
          fontWeight: 400,
          color,
          opacity: 0.7,
          lineHeight: 1.5,
        }}
      >
        {en}
      </div>
    </div>
  );
};
