import React from "react";
import { AbsoluteFill, Series } from "remotion";
import { Locale } from "./styles";
import { AskSequence } from "./sequences/AskSequence";
import { CTASequence } from "./sequences/CTASequence";
import { GraphSequence } from "./sequences/GraphSequence";
import { HookSequence } from "./sequences/HookSequence";
import { TrustSequence } from "./sequences/TrustSequence";
import { TurnSequence } from "./sequences/TurnSequence";
import { UploadSequence } from "./sequences/UploadSequence";

type VideoProps = {
  locale: Locale;
};

export const Video: React.FC<VideoProps> = ({ locale }) => {
  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={420}>
          <HookSequence locale={locale} />
        </Series.Sequence>
        <Series.Sequence durationInFrames={120}>
          <TurnSequence locale={locale} />
        </Series.Sequence>
        <Series.Sequence durationInFrames={180}>
          <UploadSequence locale={locale} />
        </Series.Sequence>
        <Series.Sequence durationInFrames={240}>
          <GraphSequence locale={locale} />
        </Series.Sequence>
        <Series.Sequence durationInFrames={240}>
          <AskSequence locale={locale} />
        </Series.Sequence>
        <Series.Sequence durationInFrames={240}>
          <TrustSequence locale={locale} />
        </Series.Sequence>
        <Series.Sequence durationInFrames={210}>
          <CTASequence locale={locale} />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
