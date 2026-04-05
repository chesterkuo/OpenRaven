import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { ChatBubble } from "../components/ChatBubble";
import { TypewriterText } from "../components/TypewriterText";
import { fontBody, fontChinese } from "../fonts";
import { colors, Locale } from "../styles";

const QUESTION = "上次我怎麼處理 NDA 的智慧財產條款？";
const QUESTION_EN = "How did I handle the IP clause in the NDA last time?";

const ANSWER = "根據您 2025 年 3 月的備忘錄，您在 NDA 中加入了「雙向 IP 保護條款」，要求雙方在合作期間產生的智慧財產歸屬依貢獻比例分配，並設定了 12 個月的競業限制期。";
const ANSWER_EN = "Based on your March 2025 memo, you added a 'bilateral IP protection clause' to the NDA...";

const SOURCE = "[Source: NDA_備忘錄_2025Q1.pdf:1240-1890]";

// Thinking dots animation
const ThinkingDots: React.FC<{ delay: number }> = ({ delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const opacity = spring({
    frame: frame - delay,
    fps,
    from: 0,
    to: 1,
    config: { damping: 20 },
  });

  return (
    <div style={{ opacity, display: "flex", gap: 6, padding: "8px 0" }}>
      {[0, 1, 2].map((i) => {
        const dotOpacity = interpolate(
          ((frame - delay) % 24) - i * 4,
          [0, 8],
          [0.3, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );
        return (
          <div
            key={i}
            style={{
              width: 8,
              height: 8,
              borderRadius: 4,
              backgroundColor: colors.textMuted,
              opacity: dotOpacity,
            }}
          />
        );
      })}
    </div>
  );
};

type AskSequenceProps = {
  locale?: Locale;
};

export const AskSequence: React.FC<AskSequenceProps> = ({ locale = "zh" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const QUESTION_DONE = 70;  // Question finishes typing
  const THINKING_START = 80;
  const ANSWER_START = 110;
  const SOURCE_START = 200;

  const sourceOpacity = spring({
    frame: frame - SOURCE_START,
    fps,
    from: 0,
    to: 1,
    config: { damping: 15, stiffness: 120 },
  });

  const primaryQuestion = locale === "zh" ? QUESTION : QUESTION_EN;
  const subQuestion = locale === "zh" ? QUESTION_EN : QUESTION;
  const primaryQuestionFont = locale === "zh" ? fontChinese : fontBody;
  const subQuestionFont = locale === "zh" ? fontBody : fontChinese;

  const primaryAnswer = locale === "zh" ? ANSWER : ANSWER_EN;
  const subAnswer = locale === "zh" ? ANSWER_EN : ANSWER;
  const primaryAnswerFont = locale === "zh" ? fontChinese : fontBody;
  const subAnswerFont = locale === "zh" ? fontBody : fontChinese;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.warmCream,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "80px 300px",
      }}
    >
      {/* Mode indicator */}
      <div
        style={{
          fontFamily: fontBody,
          fontSize: 14,
          color: colors.textMuted,
          marginBottom: 24,
          textTransform: "uppercase",
          letterSpacing: 1,
        }}
      >
        Mode: Mix
      </div>

      {/* User question */}
      <ChatBubble role="user" delay={0}>
        <TypewriterText text={primaryQuestion} startFrame={5} speed={2} style={{ fontFamily: primaryQuestionFont }} />
        {frame > QUESTION_DONE && (
          <div
            style={{
              fontFamily: subQuestionFont,
              fontSize: 16,
              opacity: 0.7,
              marginTop: 4,
            }}
          >
            {subQuestion}
          </div>
        )}
      </ChatBubble>

      {/* Thinking dots */}
      {frame >= THINKING_START && frame < ANSWER_START && (
        <ChatBubble role="assistant" delay={THINKING_START}>
          <ThinkingDots delay={THINKING_START} />
        </ChatBubble>
      )}

      {/* Assistant answer */}
      {frame >= ANSWER_START && (
        <ChatBubble role="assistant" delay={ANSWER_START}>
          <TypewriterText
            text={primaryAnswer}
            startFrame={ANSWER_START}
            speed={1}
            style={{ fontFamily: primaryAnswerFont }}
          />
          {frame > ANSWER_START + 60 && (
            <div
              style={{
                fontFamily: subAnswerFont,
                fontSize: 15,
                color: colors.textMuted,
                marginTop: 8,
              }}
            >
              {subAnswer}
            </div>
          )}

          {/* Source citation badge */}
          {frame >= SOURCE_START && (
            <div
              style={{
                marginTop: 12,
                opacity: sourceOpacity,
                display: "inline-block",
                padding: "4px 12px",
                backgroundColor: "rgba(250,82,15,0.1)",
                borderRadius: 6,
                fontFamily: fontBody,
                fontSize: 13,
                color: colors.brand,
                fontWeight: 500,
              }}
            >
              {SOURCE}
            </div>
          )}
        </ChatBubble>
      )}
    </AbsoluteFill>
  );
};
