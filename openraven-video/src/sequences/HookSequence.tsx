import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { FadeIn } from "../components/FadeIn";
import { fontBody, fontChinese } from "../fonts";
import { colors, Locale } from "../styles";

const lines = [
  {
    zh: "那些年累積的判斷力、踩過的坑、解過的難題——",
    en: "Years of hard-won judgment, lessons learned, problems solved —",
    delay: 15,
  },
  {
    zh: "有多少還記得住？",
    en: "How much do you still remember?",
    delay: 90,
  },
  {
    zh: "有多少已經消失在 Email 堆、舊報告",
    en: "How much has vanished into email threads, old reports,",
    delay: 180,
  },
  {
    zh: "和離職的前同事身上？",
    en: "and former colleagues who left?",
    delay: 240,
  },
];

// Floating document shapes for background ambiance
const FloatingDoc: React.FC<{ x: number; y: number; delay: number; size: number }> = ({
  x, y, delay, size,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [delay, delay + 60, 300, 420], [0, 0.08, 0.08, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const drift = interpolate(frame, [0, 420], [0, -40]);

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y + drift,
        width: size,
        height: size * 1.3,
        border: "1px solid rgba(255,255,255,0.15)",
        borderRadius: 4,
        opacity,
      }}
    />
  );
};

const docs = [
  { x: 120, y: 200, delay: 0, size: 60 },
  { x: 1650, y: 350, delay: 20, size: 50 },
  { x: 400, y: 700, delay: 40, size: 45 },
  { x: 1300, y: 150, delay: 10, size: 55 },
  { x: 800, y: 800, delay: 30, size: 40 },
  { x: 1750, y: 650, delay: 50, size: 48 },
];

type HookSequenceProps = {
  locale?: Locale;
};

export const HookSequence: React.FC<HookSequenceProps> = ({ locale = "zh" }) => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.dark,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {docs.map((d, i) => (
        <FloatingDoc key={i} {...d} />
      ))}

      <div style={{ maxWidth: 1200, padding: 80 }}>
        {lines.map((line, i) => (
          <FadeIn key={i} delay={line.delay} direction="up">
            <div style={{ marginBottom: 32 }}>
              <div
                style={{
                  fontFamily: locale === "zh" ? fontChinese : fontBody,
                  fontSize: 46,
                  fontWeight: 700,
                  color: colors.white,
                  lineHeight: 1.5,
                }}
              >
                {locale === "zh" ? line.zh : line.en}
              </div>
              <div
                style={{
                  fontFamily: locale === "zh" ? fontBody : fontChinese,
                  fontSize: 20,
                  color: colors.textLight,
                  lineHeight: 1.5,
                  marginTop: 4,
                }}
              >
                {locale === "zh" ? line.en : line.zh}
              </div>
            </div>
          </FadeIn>
        ))}
      </div>
    </AbsoluteFill>
  );
};
