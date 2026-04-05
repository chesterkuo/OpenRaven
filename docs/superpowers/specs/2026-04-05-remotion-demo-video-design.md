# OpenRaven Demo Video — Design Spec

## Overview

A 55-second promotional video built with [Remotion](https://github.com/remotion-dev/remotion) (React framework for programmatic video) showcasing OpenRaven's core features: document ingestion, knowledge graph, and AI Q&A.

**Format:** 1920x1080 (16:9), 30fps, MP4 (H.264), silent (no audio)
**Language:** Bilingual — Traditional Chinese narrative text (large) + English subtitles (small)
**Style:** Problem → Solution storytelling arc with actual product UI as proof points
**Target:** LinkedIn, pitch decks, social media (30-60s format)

## Storyboard

### Beat 1-2 — The Hook + Pain (0-14s)

**Text (ZH):**
> 那些年累積的判斷力、踩過的坑、解過的難題——
> 有多少還記得住？有多少已經消失在 Email 堆、舊報告和離職的前同事身上？

**Text (EN):**
> Years of hard-won judgment, lessons learned, problems solved — How much do you still remember? How much has vanished into email threads, old reports, and former colleagues?

**Visual:** Dark background (#1a1a1a). Text fades in line by line with spring animation. Subtle floating document shapes in background slowly dissolving. Mood: loss, urgency.

**Method:** Motion graphics (Remotion spring/interpolate)

### Beat 3 — The Turn (14-18s)

**Text (ZH):** 我們正在打造 OpenRaven。一個 AI 知識編譯器。
**Text (EN):** We're building OpenRaven. An AI knowledge compiler.

**Visual:** Background transitions from dark (#1a1a1a) to warm cream (#fef9ef). BlockLogo (4 gradient bars: #ffd900, #ffa110, #fb6424, #fa520f) animates in — bars slide in one by one, left to right. "OpenRaven" text fades in beside it.

**Method:** Motion graphics

### Beat 4 — Upload (18-24s)

**Text (ZH):** 上傳報告、備忘錄、會議記錄
**Text (EN):** Upload reports, memos, meeting notes

**Visual:** Simplified Ingest page UI centered on screen (~80% scale). Animated file icons (PDF, DOCX, PPTX) drop into upload zone with spring physics. Progress bar fills. Stats counter ticks: "12 Files · 847 Entities · 32 Articles".

**Method:** Screenshot of Ingest page + animated overlays

### Beat 5 — Knowledge Graph (24-32s) ★ Hero Moment

**Text (ZH):** AI 自動萃取概念、建立連結、生成可查詢的知識庫
**Text (EN):** AI extracts concepts, builds connections, generates a queryable knowledge base

**Visual:** MiniGraph component — ~40 nodes appear one by one with spring animation. Edges draw in between them. Color-coded by entity type (Technology: #fa520f, Concept: #1f1f1f, Person: #ffa110, Organization: #d94800). Nodes drift with d3-force simulation. Camera slowly zooms in. Quick 1s flash of Wiki page showing auto-generated articles.

**Method:** Recreated in React (MiniGraph component + d3-force)

### Beat 6 — The Ask (32-40s) ★ Hero Moment

**Text (ZH):** 問它「上次我怎麼處理這個問題？」——它知道答案
**Text (EN):** "How did I handle this last time?" — It knows.

**Visual:** Simplified Ask page UI. TypewriterText types out a question character by character. Brief pause with "thinking" dots animation. Response streams in word by word. Source citation badges ([Source: contract.pdf]) pop in at end. User bubble: orange gradient (#fb6424 → #fa520f). Assistant bubble: white with golden shadow.

**Method:** Recreated in React (TypewriterText + ChatBubble components)

### Beat 7 — Trust (40-48s)

**Text (ZH):** 開源 · E2EE 加密 · 支援本地 LLM
**Text (EN):** Open Source (Apache 2.0) · E2E Encrypted · Local LLM Support

**Visual:** Three trust badges slide in from bottom, staggered 0.3s apart. Each badge: SVG icon + Chinese label (large) + English label (small). Clean, authoritative. Background: warm cream.

**Method:** Motion graphics

### Beat 8 — CTA (48-55s)

**Text (ZH):** 為律師、分析師、顧問、工程師而建。你的職涯知識，不應該隨人走。
**Text (EN):** Built for lawyers, analysts, consultants, engineers. Your career knowledge shouldn't walk away with people.

**Visual:** Dark background returns (#1f1f1f). Tagline holds 3s center screen. BlockLogo + "OpenRaven" fades in below. URL "openraven.cc" in warm amber (#ffa110). Holds 2s. Fade to black.

**Method:** Motion graphics

## Project Structure

```
openraven-video/
├── package.json
├── tsconfig.json
├── remotion.config.ts
├── src/
│   ├── Root.tsx                    # Composition registry
│   ├── Video.tsx                   # Main 55s composition, sequences all beats
│   ├── sequences/
│   │   ├── HookSequence.tsx        # Beat 1-2: dark mood, problem text
│   │   ├── TurnSequence.tsx        # Beat 3: logo reveal, dark→warm transition
│   │   ├── UploadSequence.tsx      # Beat 4: screenshot + file drop animation
│   │   ├── GraphSequence.tsx       # Beat 5: recreated graph animation
│   │   ├── AskSequence.tsx         # Beat 6: recreated typing + streaming response
│   │   ├── TrustSequence.tsx       # Beat 7: three trust badges
│   │   └── CTASequence.tsx         # Beat 8: tagline + URL
│   ├── components/
│   │   ├── MiniGraph.tsx           # Simplified force graph (SVG, not canvas)
│   │   ├── TypewriterText.tsx      # Character-by-character text reveal
│   │   ├── ChatBubble.tsx          # Styled message bubble (user/assistant)
│   │   ├── BlockLogo.tsx           # 4-bar brand logo animation
│   │   ├── TrustBadge.tsx          # Icon + bilingual label
│   │   ├── Caption.tsx             # Bilingual text overlay (ZH large + EN small)
│   │   ├── FadeIn.tsx              # Reusable spring fade-in wrapper
│   │   └── Counter.tsx             # Animated number counter
│   ├── assets/
│   │   └── screenshots/            # demo-graph.png, demo-ask.png, demo-documents.png
│   └── styles.ts                   # Design tokens (colors, fonts, spacing)
```

## Design Tokens

```typescript
export const colors = {
  dark: '#1a1a1a',
  warmCream: '#fef9ef',
  brand: '#fa520f',
  brandFlame: '#fb6424',
  brandAmber: '#ffa110',
  brandGold: '#ffd900',
  text: '#1f1f1f',
  textMuted: '#666666',
  white: '#ffffff',
};

export const fonts = {
  body: 'DM Sans',        // English + UI text
  chinese: 'Noto Sans TC', // Chinese narrative text
};
```

## Technical Decisions

- **SVG for MiniGraph, not Canvas:** Remotion renders frame-by-frame, so Canvas animation state is hard to manage. SVG nodes/edges are React elements — natural fit for Remotion's declarative model.
- **d3-force for graph layout:** Pre-compute node positions using d3-force simulation, then animate nodes appearing at those positions. No live simulation during render — positions are deterministic.
- **spring() for all motion:** Remotion's spring() function for fade-ins, slide-ins, scale-ups. Consistent, natural feel throughout.
- **interpolate() for transitions:** Background color shift (dark→warm), opacity fades, zoom effects.
- **@remotion/google-fonts:** Load DM Sans and Noto Sans TC without manual font file management.
- **staticFile() for screenshots:** Place demo screenshots in public/ and reference via Remotion's staticFile().

## Rendering

```bash
# Preview in browser
npx remotion preview

# Render final MP4
npx remotion render Video --codec h264
```

Output: `out/Video.mp4` (1920x1080, 30fps, ~55s, silent)

## Dependencies

```json
{
  "remotion": "^4.x",
  "@remotion/cli": "^4.x",
  "@remotion/google-fonts": "^4.x",
  "d3-force": "^3.0.0",
  "d3-quadtree": "^3.0.1",
  "react": "^19.0.0",
  "react-dom": "^19.0.0",
  "typescript": "^5.x"
}
```

## Out of Scope

- Audio / voiceover (silent video, audio can be added in post-production)
- Subtitles file (SRT/VTT) — text is baked into the video
- Mobile-optimized vertical version (1080x1920) — can be a follow-up
- Interactive elements — this is a rendered MP4, not a web experience
