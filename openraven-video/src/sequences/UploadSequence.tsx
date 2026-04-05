import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Caption } from "../components/Caption";
import { Counter } from "../components/Counter";
import { FadeIn } from "../components/FadeIn";
import { fontBody } from "../fonts";
import { colors } from "../styles";

const FILE_ICONS = [
  { name: "報告.pdf", color: "#dc2626", delay: 30 },
  { name: "備忘錄.docx", color: "#2563eb", delay: 45 },
  { name: "會議記錄.pptx", color: "#d97706", delay: 60 },
];

const FileIcon: React.FC<{ name: string; color: string; delay: number }> = ({
  name, color, delay,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const drop = spring({
    frame: frame - delay,
    fps,
    from: -200,
    to: 0,
    config: { damping: 12, stiffness: 80 },
  });

  const opacity = spring({
    frame: frame - delay,
    fps,
    from: 0,
    to: 1,
    config: { damping: 20 },
  });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 8,
        opacity,
        transform: `translateY(${drop}px)`,
      }}
    >
      <div
        style={{
          width: 72,
          height: 90,
          backgroundColor: color,
          borderRadius: 8,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <div style={{ color: "#fff", fontFamily: fontBody, fontSize: 14, fontWeight: 700 }}>
          {name.split(".")[1]?.toUpperCase()}
        </div>
      </div>
      <div style={{ fontFamily: fontBody, fontSize: 14, color: colors.text }}>{name}</div>
    </div>
  );
};

export const UploadSequence: React.FC = () => {
  const frame = useCurrentFrame();

  // Progress bar fill
  const progress = interpolate(frame, [80, 130], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.warmCream,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        gap: 40,
      }}
    >
      <FadeIn delay={0}>
        <Caption
          zh="上傳報告、備忘錄、會議記錄"
          en="Upload reports, memos, meeting notes"
          color={colors.text}
        />
      </FadeIn>

      {/* Upload zone mockup */}
      <div
        style={{
          width: 600,
          padding: 40,
          border: `2px dashed ${colors.brandAmber}`,
          borderRadius: 12,
          backgroundColor: "rgba(255,240,194,0.3)",
          display: "flex",
          justifyContent: "center",
          gap: 40,
        }}
      >
        {FILE_ICONS.map((f) => (
          <FileIcon key={f.name} {...f} />
        ))}
      </div>

      {/* Progress bar */}
      <div
        style={{
          width: 500,
          height: 8,
          backgroundColor: "rgba(0,0,0,0.08)",
          borderRadius: 4,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${progress}%`,
            height: "100%",
            backgroundColor: colors.brand,
            borderRadius: 4,
          }}
        />
      </div>

      {/* Stats counters */}
      {frame > 110 && (
        <FadeIn delay={110}>
          <div style={{ display: "flex", gap: 80 }}>
            <Counter to={12} startFrame={115} label="Files" color={colors.text} />
            <Counter to={847} startFrame={120} label="Entities" color={colors.text} />
            <Counter to={32} startFrame={125} label="Articles" color={colors.text} />
          </div>
        </FadeIn>
      )}
    </AbsoluteFill>
  );
};
