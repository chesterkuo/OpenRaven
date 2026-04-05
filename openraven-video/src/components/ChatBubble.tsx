import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { fontBody, fontChinese } from "../fonts";
import { colors } from "../styles";

type ChatBubbleProps = {
  role: "user" | "assistant";
  children: React.ReactNode;
  delay?: number;
};

export const ChatBubble: React.FC<ChatBubbleProps> = ({ role, children, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = spring({
    frame: frame - delay,
    fps,
    from: 0,
    to: 1,
    config: { damping: 20 },
  });

  const isUser = role === "user";

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        opacity,
        marginBottom: 16,
      }}
    >
      <div
        style={{
          maxWidth: 700,
          padding: "16px 24px",
          borderRadius: 16,
          fontFamily: fontChinese,
          fontSize: 22,
          lineHeight: 1.6,
          ...(isUser
            ? {
                background: `linear-gradient(135deg, ${colors.brandFlame}, ${colors.brand})`,
                color: colors.white,
              }
            : {
                backgroundColor: colors.white,
                color: colors.text,
                boxShadow: "rgba(127,99,21,0.08) -4px 8px 20px",
              }),
        }}
      >
        {children}
      </div>
    </div>
  );
};
