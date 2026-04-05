import React from "react";
import { AbsoluteFill, Series } from "remotion";
import { AskSequence } from "./sequences/AskSequence";
import { CTASequence } from "./sequences/CTASequence";
import { GraphSequence } from "./sequences/GraphSequence";
import { HookSequence } from "./sequences/HookSequence";
import { TrustSequence } from "./sequences/TrustSequence";
import { TurnSequence } from "./sequences/TurnSequence";
import { UploadSequence } from "./sequences/UploadSequence";

export const Video: React.FC = () => {
  return (
    <AbsoluteFill>
      <Series>
        <Series.Sequence durationInFrames={420}>
          <HookSequence />
        </Series.Sequence>
        <Series.Sequence durationInFrames={120}>
          <TurnSequence />
        </Series.Sequence>
        <Series.Sequence durationInFrames={180}>
          <UploadSequence />
        </Series.Sequence>
        <Series.Sequence durationInFrames={240}>
          <GraphSequence />
        </Series.Sequence>
        <Series.Sequence durationInFrames={240}>
          <AskSequence />
        </Series.Sequence>
        <Series.Sequence durationInFrames={240}>
          <TrustSequence />
        </Series.Sequence>
        <Series.Sequence durationInFrames={210}>
          <CTASequence />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
