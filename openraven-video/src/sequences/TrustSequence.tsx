import React from "react";
import { AbsoluteFill } from "remotion";
import { Caption } from "../components/Caption";
import { FadeIn } from "../components/FadeIn";
import { TrustBadge } from "../components/TrustBadge";
import { colors, Locale } from "../styles";

// SVG icons (simple, clean)
const OpenSourceIcon = (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
    <circle cx="32" cy="32" r="28" stroke={colors.brand} strokeWidth="3" />
    <circle cx="32" cy="24" r="8" fill={colors.brand} />
    <path d="M20 48c0-8 5.5-14 12-14s12 6 12 14" stroke={colors.brand} strokeWidth="3" strokeLinecap="round" />
  </svg>
);

const EncryptionIcon = (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
    <rect x="16" y="28" width="32" height="24" rx="4" fill={colors.brandAmber} />
    <path d="M24 28V20a8 8 0 1116 0v8" stroke={colors.brandAmber} strokeWidth="3" strokeLinecap="round" />
    <circle cx="32" cy="40" r="4" fill="white" />
  </svg>
);

const LocalLLMIcon = (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
    <rect x="18" y="14" width="28" height="36" rx="4" stroke={colors.brandGold} strokeWidth="3" />
    <line x1="24" y1="24" x2="40" y2="24" stroke={colors.brandGold} strokeWidth="2" />
    <line x1="24" y1="32" x2="40" y2="32" stroke={colors.brandGold} strokeWidth="2" />
    <line x1="24" y1="40" x2="34" y2="40" stroke={colors.brandGold} strokeWidth="2" />
    <circle cx="32" cy="56" r="4" fill={colors.brandGold} />
  </svg>
);

type TrustSequenceProps = {
  locale?: Locale;
};

export const TrustSequence: React.FC<TrustSequenceProps> = ({ locale = "zh" }) => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.warmCream,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        gap: 60,
      }}
    >
      <FadeIn delay={0}>
        <Caption
          zh="值得信賴的技術基礎"
          en="A trustworthy technical foundation"
          locale={locale}
          color={colors.text}
        />
      </FadeIn>

      <div style={{ display: "flex", gap: 80 }}>
        <TrustBadge icon={OpenSourceIcon} zh="核心引擎開源" en="Apache 2.0 License" delay={20} locale={locale} />
        <TrustBadge icon={EncryptionIcon} zh="E2EE 加密" en="Zero-knowledge encryption" delay={30} locale={locale} />
        <TrustBadge icon={LocalLLMIcon} zh="支援本地 LLM" en="No cloud required" delay={40} locale={locale} />
      </div>
    </AbsoluteFill>
  );
};
