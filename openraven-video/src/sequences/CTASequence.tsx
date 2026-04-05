import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BlockLogo } from "../components/BlockLogo";
import { FadeIn } from "../components/FadeIn";
import { fontBody, fontChinese } from "../fonts";
import { colors } from "../styles";

export const CTASequence: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Fade to black at the very end
  const fadeOut = interpolate(frame, [180, 210], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const urlOpacity = spring({
    frame: frame - 100,
    fps,
    from: 0,
    to: 1,
    config: { damping: 20 },
  });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.dark }}>
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          gap: 40,
        }}
      >
        {/* Professions line */}
        <FadeIn delay={5}>
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                fontFamily: fontChinese,
                fontSize: 32,
                color: colors.white,
                opacity: 0.8,
              }}
            >
              為律師、分析師、顧問、工程師而建
            </div>
            <div
              style={{
                fontFamily: fontBody,
                fontSize: 18,
                color: colors.textLight,
                marginTop: 8,
              }}
            >
              Built for lawyers, analysts, consultants, engineers
            </div>
          </div>
        </FadeIn>

        {/* Main tagline */}
        <FadeIn delay={30}>
          <div
            style={{
              fontFamily: fontChinese,
              fontSize: 52,
              fontWeight: 700,
              color: colors.white,
              textAlign: "center",
              lineHeight: 1.4,
            }}
          >
            你的職涯知識，不應該隨人走。
          </div>
          <div
            style={{
              fontFamily: fontBody,
              fontSize: 22,
              color: colors.textLight,
              textAlign: "center",
              marginTop: 8,
            }}
          >
            Your career knowledge shouldn't walk away with people.
          </div>
        </FadeIn>

        {/* Logo + URL */}
        <FadeIn delay={70}>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 20,
            }}
          >
            <BlockLogo size={60} delay={70} />
            <div
              style={{
                fontFamily: fontBody,
                fontSize: 20,
                fontWeight: 700,
                color: colors.white,
                letterSpacing: 1,
              }}
            >
              OpenRaven
            </div>
          </div>
        </FadeIn>

        {/* URL */}
        <div
          style={{
            opacity: urlOpacity,
            fontFamily: fontBody,
            fontSize: 28,
            fontWeight: 500,
            color: colors.brandAmber,
          }}
        >
          openraven.cc
        </div>
      </AbsoluteFill>

      {/* Final fade to black */}
      <AbsoluteFill
        style={{
          backgroundColor: colors.dark,
          opacity: fadeOut,
        }}
      />
    </AbsoluteFill>
  );
};
