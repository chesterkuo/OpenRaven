# OpenRaven Demo Video — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 55-second promotional video using Remotion (React) that showcases OpenRaven's document ingestion, knowledge graph, and AI Q&A features in a problem→solution narrative.

**Architecture:** Remotion project (`openraven-video/`) at repo root. Main `Video` composition sequences 7 scene components via `<Series>`. Two hero moments (graph + ask) are recreated as React components; other scenes use motion graphics and screenshot overlays. All animation via Remotion `spring()` and `interpolate()`.

**Tech Stack:** Remotion 4.x, React 19, TypeScript, d3-force (graph layout), @remotion/google-fonts (DM Sans + Noto Sans TC)

---

## File Structure

```
openraven-video/
├── package.json
├── tsconfig.json
├── remotion.config.ts
├── src/
│   ├── index.ts                     # registerRoot entry
│   ├── Root.tsx                     # Composition registry
│   ├── Video.tsx                    # Main composition — sequences all beats
│   ├── styles.ts                    # Design tokens (colors, fonts)
│   ├── fonts.ts                     # Font loading (DM Sans + Noto Sans TC)
│   ├── sequences/
│   │   ├── HookSequence.tsx         # Beat 1-2: dark background, problem text
│   │   ├── TurnSequence.tsx         # Beat 3: logo reveal, dark→warm
│   │   ├── UploadSequence.tsx       # Beat 4: screenshot + file drop animation
│   │   ├── GraphSequence.tsx        # Beat 5: recreated graph (hero)
│   │   ├── AskSequence.tsx          # Beat 6: recreated chat (hero)
│   │   ├── TrustSequence.tsx        # Beat 7: trust badges
│   │   └── CTASequence.tsx          # Beat 8: tagline + URL
│   └── components/
│       ├── Caption.tsx              # Bilingual text (ZH large + EN small)
│       ├── FadeIn.tsx               # Reusable spring fade-in wrapper
│       ├── BlockLogo.tsx            # 4-bar brand logo
│       ├── MiniGraph.tsx            # SVG force graph with animated nodes
│       ├── TypewriterText.tsx       # Character-by-character text
│       ├── ChatBubble.tsx           # User/assistant message bubble
│       ├── TrustBadge.tsx           # Icon + bilingual label
│       └── Counter.tsx              # Animated number counter
├── public/
│   └── screenshots/
│       ├── demo-graph.png
│       ├── demo-ask.png
│       └── demo-documents.png
```

---

## Task 1: Scaffold Remotion Project

**Files:**
- Create: `openraven-video/package.json`
- Create: `openraven-video/tsconfig.json`
- Create: `openraven-video/remotion.config.ts`
- Create: `openraven-video/src/index.ts`
- Create: `openraven-video/src/Root.tsx`

- [ ] **Step 1: Create project directory and package.json**

```bash
mkdir -p openraven-video/src openraven-video/public/screenshots
```

Write `openraven-video/package.json`:

```json
{
  "name": "openraven-video",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "preview": "remotion preview src/index.ts",
    "render": "remotion render src/index.ts Video out/Video.mp4",
    "build": "remotion render src/index.ts Video out/Video.mp4 --codec h264"
  },
  "dependencies": {
    "@remotion/cli": "^4.0.0",
    "@remotion/google-fonts": "^4.0.0",
    "d3-force": "^3.0.0",
    "d3-quadtree": "^3.0.1",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "remotion": "^4.0.0"
  },
  "devDependencies": {
    "@types/d3-force": "^3.0.0",
    "@types/react": "^19.0.0",
    "typescript": "^5.0.0"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

Write `openraven-video/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "outDir": "./dist"
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create remotion.config.ts**

Write `openraven-video/remotion.config.ts`:

```ts
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
```

- [ ] **Step 4: Create entry point and Root**

Write `openraven-video/src/index.ts`:

```ts
import { registerRoot } from "remotion";
import { Root } from "./Root";

registerRoot(Root);
```

Write `openraven-video/src/Root.tsx` (placeholder — will wire up Video in Task 3):

```tsx
import React from "react";
import { Composition } from "remotion";
import { AbsoluteFill } from "remotion";

const Placeholder: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: "#1a1a1a", color: "#fff", display: "flex", justifyContent: "center", alignItems: "center", fontSize: 48 }}>
    OpenRaven Video
  </AbsoluteFill>
);

export const Root: React.FC = () => {
  return (
    <Composition
      id="Video"
      component={Placeholder}
      durationInFrames={1650}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
```

- [ ] **Step 5: Copy screenshots to public/**

```bash
cp screenshots/demo-graph.png openraven-video/public/screenshots/
cp screenshots/demo-ask.png openraven-video/public/screenshots/
cp screenshots/demo-documents.png openraven-video/public/screenshots/
```

- [ ] **Step 6: Install dependencies and verify preview launches**

```bash
cd openraven-video && npm install
npx remotion preview src/index.ts
```

Expected: Preview server starts, shows dark screen with "OpenRaven Video" text.

- [ ] **Step 7: Commit**

```bash
git add openraven-video/
git commit -m "feat(video): scaffold Remotion project for demo video"
```

---

## Task 2: Design Tokens, Fonts, and Shared Components

**Files:**
- Create: `openraven-video/src/styles.ts`
- Create: `openraven-video/src/fonts.ts`
- Create: `openraven-video/src/components/Caption.tsx`
- Create: `openraven-video/src/components/FadeIn.tsx`
- Create: `openraven-video/src/components/BlockLogo.tsx`

- [ ] **Step 1: Create design tokens**

Write `openraven-video/src/styles.ts`:

```ts
export const colors = {
  dark: "#1a1a1a",
  warmCream: "#fef9ef",
  brand: "#fa520f",
  brandFlame: "#fb6424",
  brandAmber: "#ffa110",
  brandGold: "#ffd900",
  text: "#1f1f1f",
  textMuted: "#666666",
  textLight: "#999999",
  white: "#ffffff",
  darkOrange: "#d94800",
  gold: "#b8860b",
};

export const FRAME_RATE = 30;

// Beat timing in frames (at 30fps)
export const beats = {
  hook:  { from: 0,    duration: 420  }, // 0-14s
  turn:  { from: 420,  duration: 120  }, // 14-18s
  upload:{ from: 540,  duration: 180  }, // 18-24s
  graph: { from: 720,  duration: 240  }, // 24-32s
  ask:   { from: 960,  duration: 240  }, // 32-40s
  trust: { from: 1200, duration: 240  }, // 40-48s
  cta:   { from: 1440, duration: 210  }, // 48-55s
};

export const TOTAL_FRAMES = 1650; // 55s at 30fps
```

- [ ] **Step 2: Create font loading**

Write `openraven-video/src/fonts.ts`:

```ts
import { loadFont as loadDMSans } from "@remotion/google-fonts/DMSans";
import { loadFont as loadNotoSansTC } from "@remotion/google-fonts/NotoSansTC";
import { cancelRender, continueRender, delayRender } from "remotion";

const dmSans = loadDMSans("normal", {
  weights: ["400", "500", "700"],
  subsets: ["latin"],
});

const notoSansTC = loadNotoSansTC("normal", {
  weights: ["400", "500", "700"],
  subsets: ["chinese-traditional"],
});

export const fontBody = dmSans.fontFamily;
export const fontChinese = notoSansTC.fontFamily;

const delay = delayRender("Loading fonts");

Promise.all([dmSans.waitUntilDone(), notoSansTC.waitUntilDone()])
  .then(() => continueRender(delay))
  .catch((err) => cancelRender(err));
```

- [ ] **Step 3: Create Caption component**

Write `openraven-video/src/components/Caption.tsx`:

```tsx
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
```

- [ ] **Step 4: Create FadeIn wrapper**

Write `openraven-video/src/components/FadeIn.tsx`:

```tsx
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

type FadeInProps = {
  delay?: number;
  direction?: "up" | "down" | "none";
  distance?: number;
  children: React.ReactNode;
};

export const FadeIn: React.FC<FadeInProps> = ({
  delay = 0,
  direction = "up",
  distance = 30,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = spring({
    frame: frame - delay,
    fps,
    from: 0,
    to: 1,
    config: { damping: 20, stiffness: 80 },
  });

  const translateY =
    direction === "none"
      ? 0
      : interpolate(opacity, [0, 1], [direction === "up" ? distance : -distance, 0]);

  return (
    <div style={{ opacity, transform: `translateY(${translateY}px)` }}>
      {children}
    </div>
  );
};
```

- [ ] **Step 5: Create BlockLogo component**

Write `openraven-video/src/components/BlockLogo.tsx`:

```tsx
import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors } from "../styles";

type BlockLogoProps = {
  size?: number;
  delay?: number;
};

const BAR_COLORS = [colors.brandGold, colors.brandAmber, colors.brandFlame, colors.brand];

export const BlockLogo: React.FC<BlockLogoProps> = ({ size = 48, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ display: "flex", gap: size * 0.1 }}>
      {BAR_COLORS.map((color, i) => {
        const scale = spring({
          frame: frame - delay - i * 4,
          fps,
          from: 0,
          to: 1,
          config: { damping: 12, stiffness: 120 },
        });

        return (
          <div
            key={i}
            style={{
              width: size * 0.18,
              height: size,
              backgroundColor: color,
              borderRadius: size * 0.05,
              transform: `scaleY(${scale})`,
              transformOrigin: "bottom",
            }}
          />
        );
      })}
    </div>
  );
};
```

- [ ] **Step 6: Verify components render in preview**

Update `Root.tsx` temporarily to render BlockLogo + Caption + FadeIn to confirm they work:

```bash
npx remotion preview src/index.ts
```

Expected: Logo bars animate in, caption text appears with fade-in.

- [ ] **Step 7: Commit**

```bash
git add openraven-video/src/styles.ts openraven-video/src/fonts.ts openraven-video/src/components/
git commit -m "feat(video): add design tokens, fonts, Caption, FadeIn, BlockLogo"
```

---

## Task 3: HookSequence (Beat 1-2: Problem Statement)

**Files:**
- Create: `openraven-video/src/sequences/HookSequence.tsx`

- [ ] **Step 1: Create HookSequence**

Write `openraven-video/src/sequences/HookSequence.tsx`:

```tsx
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { FadeIn } from "../components/FadeIn";
import { fontBody, fontChinese } from "../fonts";
import { colors } from "../styles";

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

export const HookSequence: React.FC = () => {
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
                  fontFamily: fontChinese,
                  fontSize: 46,
                  fontWeight: 700,
                  color: colors.white,
                  lineHeight: 1.5,
                }}
              >
                {line.zh}
              </div>
              <div
                style={{
                  fontFamily: fontBody,
                  fontSize: 20,
                  color: colors.textLight,
                  lineHeight: 1.5,
                  marginTop: 4,
                }}
              >
                {line.en}
              </div>
            </div>
          </FadeIn>
        ))}
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Verify in preview**

Temporarily render `HookSequence` in Root.tsx to confirm lines fade in staggered on dark background with floating doc shapes.

- [ ] **Step 3: Commit**

```bash
git add openraven-video/src/sequences/HookSequence.tsx
git commit -m "feat(video): add HookSequence (Beat 1-2 problem statement)"
```

---

## Task 4: TurnSequence (Beat 3: Logo Reveal)

**Files:**
- Create: `openraven-video/src/sequences/TurnSequence.tsx`

- [ ] **Step 1: Create TurnSequence**

Write `openraven-video/src/sequences/TurnSequence.tsx`:

```tsx
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BlockLogo } from "../components/BlockLogo";
import { fontBody, fontChinese } from "../fonts";
import { colors } from "../styles";

export const TurnSequence: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Background transitions from dark to warm cream
  const bgProgress = interpolate(frame, [0, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const r = interpolate(bgProgress, [0, 1], [26, 254]);
  const g = interpolate(bgProgress, [0, 1], [26, 249]);
  const b = interpolate(bgProgress, [0, 1], [26, 239]);
  const bgColor = `rgb(${r},${g},${b})`;

  // Text color transitions from white to dark
  const textR = interpolate(bgProgress, [0, 1], [255, 31]);
  const textG = interpolate(bgProgress, [0, 1], [255, 31]);
  const textB = interpolate(bgProgress, [0, 1], [255, 31]);
  const textColor = `rgb(${textR},${textG},${textB})`;

  const titleOpacity = spring({
    frame: frame - 50,
    fps,
    from: 0,
    to: 1,
    config: { damping: 20 },
  });

  const subtitleOpacity = spring({
    frame: frame - 70,
    fps,
    from: 0,
    to: 1,
    config: { damping: 20 },
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: bgColor,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 32,
      }}
    >
      <BlockLogo size={80} delay={20} />

      <div style={{ opacity: titleOpacity, textAlign: "center" }}>
        <div
          style={{
            fontFamily: fontChinese,
            fontSize: 56,
            fontWeight: 700,
            color: textColor,
          }}
        >
          我們正在打造 OpenRaven。
        </div>
        <div
          style={{
            fontFamily: fontBody,
            fontSize: 24,
            color: textColor,
            opacity: 0.6,
            marginTop: 8,
          }}
        >
          We're building OpenRaven.
        </div>
      </div>

      <div style={{ opacity: subtitleOpacity, textAlign: "center" }}>
        <div
          style={{
            fontFamily: fontChinese,
            fontSize: 36,
            fontWeight: 500,
            color: colors.brand,
          }}
        >
          一個 AI 知識編譯器
        </div>
        <div
          style={{
            fontFamily: fontBody,
            fontSize: 20,
            color: colors.brand,
            opacity: 0.7,
            marginTop: 4,
          }}
        >
          An AI knowledge compiler
        </div>
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Verify in preview**

Confirm background shifts from dark to warm cream, logo bars animate in, text appears.

- [ ] **Step 3: Commit**

```bash
git add openraven-video/src/sequences/TurnSequence.tsx
git commit -m "feat(video): add TurnSequence (Beat 3 logo reveal)"
```

---

## Task 5: UploadSequence (Beat 4: Document Ingestion)

**Files:**
- Create: `openraven-video/src/components/Counter.tsx`
- Create: `openraven-video/src/sequences/UploadSequence.tsx`

- [ ] **Step 1: Create Counter component**

Write `openraven-video/src/components/Counter.tsx`:

```tsx
import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { fontBody } from "../fonts";

type CounterProps = {
  from?: number;
  to: number;
  startFrame: number;
  duration?: number;
  label: string;
  color?: string;
};

export const Counter: React.FC<CounterProps> = ({
  from = 0,
  to,
  startFrame,
  duration = 40,
  label,
  color = "#1f1f1f",
}) => {
  const frame = useCurrentFrame();
  const value = Math.round(
    interpolate(frame, [startFrame, startFrame + duration], [from, to], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );

  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontFamily: fontBody, fontSize: 48, fontWeight: 700, color }}>
        {value.toLocaleString()}
      </div>
      <div style={{ fontFamily: fontBody, fontSize: 18, color, opacity: 0.6, marginTop: 4 }}>
        {label}
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Create UploadSequence**

Write `openraven-video/src/sequences/UploadSequence.tsx`:

```tsx
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
```

- [ ] **Step 3: Verify in preview**

Confirm file icons drop in, progress bar fills, counters tick up.

- [ ] **Step 4: Commit**

```bash
git add openraven-video/src/components/Counter.tsx openraven-video/src/sequences/UploadSequence.tsx
git commit -m "feat(video): add UploadSequence (Beat 4 document ingestion)"
```

---

## Task 6: GraphSequence + MiniGraph (Beat 5: Hero Moment)

**Files:**
- Create: `openraven-video/src/components/MiniGraph.tsx`
- Create: `openraven-video/src/sequences/GraphSequence.tsx`

- [ ] **Step 1: Create MiniGraph component**

This component pre-computes a force-directed layout, then animates nodes and edges appearing one by one using Remotion's frame-based rendering.

Write `openraven-video/src/components/MiniGraph.tsx`:

```tsx
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  SimulationNodeDatum,
} from "d3-force";
import React, { useMemo } from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors } from "../styles";

type NodeType = "technology" | "concept" | "person" | "organization" | "event" | "location";

interface GraphNode extends SimulationNodeDatum {
  id: string;
  type: NodeType;
  label: string;
}

interface GraphEdge {
  source: string;
  target: string;
}

const NODE_COLORS: Record<NodeType, string> = {
  technology: colors.brand,
  concept: colors.text,
  person: colors.brandAmber,
  organization: colors.darkOrange,
  event: colors.gold,
  location: "#8b6914",
};

// Generate deterministic sample graph data
function generateGraphData(): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const types: NodeType[] = ["technology", "concept", "person", "organization", "event", "location"];
  const labels = [
    "NDA", "GDPR", "Contract Law", "IP Rights", "Data Privacy",
    "Compliance", "Due Diligence", "Risk Assessment", "Legal AI",
    "SaaS Terms", "Arbitration", "Force Majeure", "Liability",
    "Indemnity", "Warranty", "Confidentiality", "Jurisdiction",
    "Dispute Resolution", "License", "Patent", "Copyright",
    "Trademark", "Trade Secret", "Employment Law", "Corporate Gov.",
    "Regulatory", "Audit", "Forensics", "Discovery", "Mediation",
    "Securities", "Tax Law", "Real Estate", "Insurance", "Banking",
    "Antitrust", "Environmental", "Immigration", "Consumer", "Maritime",
  ];

  const nodes: GraphNode[] = labels.map((label, i) => ({
    id: `n${i}`,
    type: types[i % types.length],
    label,
  }));

  const edges: GraphEdge[] = [];
  // Create a connected graph with clusters
  for (let i = 1; i < nodes.length; i++) {
    edges.push({ source: nodes[i].id, target: nodes[Math.floor(i / 3)].id });
    if (i % 4 === 0 && i > 4) {
      edges.push({ source: nodes[i].id, target: nodes[i - 3].id });
    }
  }

  return { nodes, edges };
}

// Pre-compute layout (runs once via useMemo)
function computeLayout(nodes: GraphNode[], edges: GraphEdge[], width: number, height: number) {
  const simNodes = nodes.map((n) => ({ ...n }));
  const simLinks = edges.map((e) => ({ source: e.source, target: e.target }));

  const sim = forceSimulation(simNodes)
    .force("link", forceLink(simLinks).id((d: any) => d.id).distance(80))
    .force("charge", forceManyBody().strength(-150))
    .force("center", forceCenter(width / 2, height / 2))
    .force("collide", forceCollide(20));

  // Run simulation to completion
  for (let i = 0; i < 300; i++) sim.tick();
  sim.stop();

  return { nodes: simNodes, links: simLinks };
}

type MiniGraphProps = {
  width?: number;
  height?: number;
};

export const MiniGraph: React.FC<MiniGraphProps> = ({ width = 1200, height = 700 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const data = useMemo(() => {
    const { nodes, edges } = generateGraphData();
    return computeLayout(nodes, edges, width, height);
  }, [width, height]);

  return (
    <svg width={width} height={height}>
      {/* Edges */}
      {data.links.map((link: any, i: number) => {
        const appearFrame = 10 + i * 3;
        const opacity = interpolate(frame, [appearFrame, appearFrame + 15], [0, 0.3], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        return (
          <line
            key={`e${i}`}
            x1={link.source.x}
            y1={link.source.y}
            x2={link.target.x}
            y2={link.target.y}
            stroke={colors.textMuted}
            strokeWidth={1}
            opacity={opacity}
          />
        );
      })}

      {/* Nodes */}
      {data.nodes.map((node: any, i: number) => {
        const appearFrame = 5 + i * 4;
        const scale = spring({
          frame: frame - appearFrame,
          fps,
          from: 0,
          to: 1,
          config: { damping: 10, stiffness: 100 },
        });

        const radius = 6 + (i < 5 ? 8 : i < 15 ? 4 : 0);
        const nodeColor = NODE_COLORS[node.type as NodeType];

        return (
          <g key={node.id} transform={`translate(${node.x},${node.y}) scale(${scale})`}>
            <circle r={radius} fill={nodeColor} />
            {radius > 8 && (
              <text
                y={radius + 14}
                textAnchor="middle"
                fontSize={11}
                fontWeight={600}
                fill={colors.text}
              >
                {node.label}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
};
```

- [ ] **Step 2: Create GraphSequence**

Write `openraven-video/src/sequences/GraphSequence.tsx`:

```tsx
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Caption } from "../components/Caption";
import { FadeIn } from "../components/FadeIn";
import { MiniGraph } from "../components/MiniGraph";
import { colors } from "../styles";

export const GraphSequence: React.FC = () => {
  const frame = useCurrentFrame();

  // Slow zoom in
  const zoom = interpolate(frame, [0, 240], [1, 1.15], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.warmCream }}>
      {/* Caption at top */}
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          zIndex: 10,
        }}
      >
        <FadeIn delay={0}>
          <Caption
            zh="AI 自動萃取概念、建立連結、生成可查詢的知識庫"
            en="AI extracts concepts, builds connections, generates a queryable knowledge base"
            zhSize={38}
            enSize={18}
            color={colors.text}
          />
        </FadeIn>
      </div>

      {/* Graph */}
      <div
        style={{
          position: "absolute",
          top: 200,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          transform: `scale(${zoom})`,
          transformOrigin: "center center",
        }}
      >
        <MiniGraph width={1400} height={680} />
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 3: Verify in preview**

Confirm nodes appear one by one with spring animation, edges fade in, camera slowly zooms.

- [ ] **Step 4: Commit**

```bash
git add openraven-video/src/components/MiniGraph.tsx openraven-video/src/sequences/GraphSequence.tsx
git commit -m "feat(video): add GraphSequence + MiniGraph (Beat 5 hero moment)"
```

---

## Task 7: AskSequence + Chat Components (Beat 6: Hero Moment)

**Files:**
- Create: `openraven-video/src/components/TypewriterText.tsx`
- Create: `openraven-video/src/components/ChatBubble.tsx`
- Create: `openraven-video/src/sequences/AskSequence.tsx`

- [ ] **Step 1: Create TypewriterText**

Write `openraven-video/src/components/TypewriterText.tsx`:

```tsx
import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

type TypewriterTextProps = {
  text: string;
  startFrame?: number;
  speed?: number; // frames per character
  style?: React.CSSProperties;
};

export const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  startFrame = 0,
  speed = 2,
  style,
}) => {
  const frame = useCurrentFrame();
  const charsToShow = Math.floor(
    interpolate(frame - startFrame, [0, text.length * speed], [0, text.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );

  return <span style={style}>{text.slice(0, charsToShow)}</span>;
};
```

- [ ] **Step 2: Create ChatBubble**

Write `openraven-video/src/components/ChatBubble.tsx`:

```tsx
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
```

- [ ] **Step 3: Create AskSequence**

Write `openraven-video/src/sequences/AskSequence.tsx`:

```tsx
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { ChatBubble } from "../components/ChatBubble";
import { TypewriterText } from "../components/TypewriterText";
import { fontBody, fontChinese } from "../fonts";
import { colors } from "../styles";

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

export const AskSequence: React.FC = () => {
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
        <TypewriterText text={QUESTION} startFrame={5} speed={2} />
        {frame > QUESTION_DONE && (
          <div
            style={{
              fontFamily: fontBody,
              fontSize: 16,
              opacity: 0.7,
              marginTop: 4,
            }}
          >
            {QUESTION_EN}
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
            text={ANSWER}
            startFrame={ANSWER_START}
            speed={1}
            style={{ fontFamily: fontChinese }}
          />
          {frame > ANSWER_START + 60 && (
            <div
              style={{
                fontFamily: fontBody,
                fontSize: 15,
                color: colors.textMuted,
                marginTop: 8,
              }}
            >
              {ANSWER_EN}
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
```

- [ ] **Step 4: Verify in preview**

Confirm question types out, thinking dots animate, answer streams in, source citation pops in.

- [ ] **Step 5: Commit**

```bash
git add openraven-video/src/components/TypewriterText.tsx openraven-video/src/components/ChatBubble.tsx openraven-video/src/sequences/AskSequence.tsx
git commit -m "feat(video): add AskSequence + chat components (Beat 6 hero moment)"
```

---

## Task 8: TrustSequence (Beat 7: Trust Badges)

**Files:**
- Create: `openraven-video/src/components/TrustBadge.tsx`
- Create: `openraven-video/src/sequences/TrustSequence.tsx`

- [ ] **Step 1: Create TrustBadge**

Write `openraven-video/src/components/TrustBadge.tsx`:

```tsx
import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { fontBody, fontChinese } from "../fonts";
import { colors } from "../styles";

type TrustBadgeProps = {
  icon: React.ReactNode;
  zh: string;
  en: string;
  delay?: number;
};

export const TrustBadge: React.FC<TrustBadgeProps> = ({ icon, zh, en, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: frame - delay,
    fps,
    from: 0,
    to: 1,
    config: { damping: 12, stiffness: 80 },
  });

  const translateY = (1 - progress) * 60;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 16,
        opacity: progress,
        transform: `translateY(${translateY}px)`,
        width: 280,
      }}
    >
      <div style={{ fontSize: 64, lineHeight: 1 }}>{icon}</div>
      <div
        style={{
          fontFamily: fontChinese,
          fontSize: 28,
          fontWeight: 700,
          color: colors.text,
        }}
      >
        {zh}
      </div>
      <div
        style={{
          fontFamily: fontBody,
          fontSize: 18,
          color: colors.textMuted,
        }}
      >
        {en}
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Create TrustSequence**

Write `openraven-video/src/sequences/TrustSequence.tsx`:

```tsx
import React from "react";
import { AbsoluteFill } from "remotion";
import { Caption } from "../components/Caption";
import { FadeIn } from "../components/FadeIn";
import { TrustBadge } from "../components/TrustBadge";
import { colors } from "../styles";

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

export const TrustSequence: React.FC = () => {
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
          color={colors.text}
        />
      </FadeIn>

      <div style={{ display: "flex", gap: 80 }}>
        <TrustBadge icon={OpenSourceIcon} zh="核心引擎開源" en="Apache 2.0 License" delay={20} />
        <TrustBadge icon={EncryptionIcon} zh="E2EE 加密" en="Zero-knowledge encryption" delay={30} />
        <TrustBadge icon={LocalLLMIcon} zh="支援本地 LLM" en="No cloud required" delay={40} />
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 3: Verify in preview**

Confirm three badges slide up staggered with SVG icons.

- [ ] **Step 4: Commit**

```bash
git add openraven-video/src/components/TrustBadge.tsx openraven-video/src/sequences/TrustSequence.tsx
git commit -m "feat(video): add TrustSequence + TrustBadge (Beat 7)"
```

---

## Task 9: CTASequence (Beat 8: Closing)

**Files:**
- Create: `openraven-video/src/sequences/CTASequence.tsx`

- [ ] **Step 1: Create CTASequence**

Write `openraven-video/src/sequences/CTASequence.tsx`:

```tsx
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
```

- [ ] **Step 2: Verify in preview**

Confirm tagline appears, logo and URL fade in, final fade to black.

- [ ] **Step 3: Commit**

```bash
git add openraven-video/src/sequences/CTASequence.tsx
git commit -m "feat(video): add CTASequence (Beat 8 closing)"
```

---

## Task 10: Wire Up Video.tsx + Root.tsx (Final Assembly)

**Files:**
- Create: `openraven-video/src/Video.tsx`
- Modify: `openraven-video/src/Root.tsx`

- [ ] **Step 1: Create Video.tsx**

Write `openraven-video/src/Video.tsx`:

```tsx
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
```

- [ ] **Step 2: Update Root.tsx**

Replace `openraven-video/src/Root.tsx` with:

```tsx
import React from "react";
import { Composition } from "remotion";
import { TOTAL_FRAMES } from "./styles";
import { Video } from "./Video";

export const Root: React.FC = () => {
  return (
    <Composition
      id="Video"
      component={Video}
      durationInFrames={TOTAL_FRAMES}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
```

- [ ] **Step 3: Full preview — scrub through all 55 seconds**

```bash
cd openraven-video && npx remotion preview src/index.ts
```

Expected: All 8 beats play in sequence. Verify:
- Beat 1-2: Dark background, text fades in line by line, floating docs
- Beat 3: Dark→warm transition, logo bars animate, title appears
- Beat 4: File icons drop, progress fills, counters tick
- Beat 5: Graph nodes spring in one by one, edges fade, zoom
- Beat 6: Question types, dots animate, answer streams, source badge pops
- Beat 7: Three trust badges slide up staggered
- Beat 8: Tagline, logo, URL, fade to black

- [ ] **Step 4: Commit**

```bash
git add openraven-video/src/Video.tsx openraven-video/src/Root.tsx
git commit -m "feat(video): wire up all sequences into Video composition"
```

---

## Task 11: Render Final MP4

**Files:** None (rendering only)

- [ ] **Step 1: Render the video**

```bash
cd openraven-video && npx remotion render src/index.ts Video out/Video.mp4 --codec h264
```

Expected: Renders 1650 frames at 1920x1080, outputs `out/Video.mp4` (~55 seconds, silent).

- [ ] **Step 2: Verify output file**

```bash
ls -lh openraven-video/out/Video.mp4
```

Expected: MP4 file, reasonable size (5-15MB for 55s at 1080p).

- [ ] **Step 3: Add out/ to .gitignore**

Append to `openraven-video/.gitignore`:

```
out/
node_modules/
```

- [ ] **Step 4: Final commit**

```bash
git add openraven-video/.gitignore
git commit -m "feat(video): add render config and gitignore"
```
