# OpenRaven UI Redesign — Mistral Premium Design Spec

**Date:** 2026-04-04
**Approach:** Option C — Mistral Premium
**Reference:** [Mistral AI DESIGN.md](https://github.com/VoltAgent/awesome-design-md/blob/main/design-md/mistral.ai/DESIGN.md)

## Overview

Full UI redesign of OpenRaven's 6-page web application, replacing the current dark-mode utility-first aesthetic with a warm, light-mode "Mistral Premium" design language. The redesign adopts Mistral AI's warm European aesthetic — ivory backgrounds, orange/amber accents, sharp architectural corners, golden multi-layer shadows — while adapting it for a productivity app context.

**Key decisions made during brainstorming:**
- Full warm light-mode adoption (no dark mode)
- All 6 pages redesigned equally
- Tailwind CSS + shadcn/ui component library (re-themed)
- Graph canvas gets the same warm ivory treatment (fully warm, no dark inversion)
- Horizontal top nav (refined, not sidebar)
- Warm bubbles with sharp corners for chat interface

## Tech Stack (unchanged except additions)

- React 19 + TypeScript + Vite 6
- Tailwind CSS 4.0 (re-configured with warm design tokens)
- **NEW:** shadcn/ui components (re-themed to Mistral warm aesthetic)
- React Router v7
- D3.js for graph visualization
- Hono + Bun backend (unchanged)

---

## 1. Design Tokens & Foundation

### 1.1 Color System

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-page` | `#fef9ef` | Page background — warm ivory |
| `--bg-surface` | `#ffffff` | Cards, panels, nav |
| `--bg-surface-warm` | `#fff0c2` | Cream accents, citation badges, secondary surfaces |
| `--bg-surface-hover` | `#fffaeb` | Hover states on warm elements |
| `--color-brand` | `#fa520f` | Mistral Orange — primary accent |
| `--color-brand-flame` | `#fb6424` | Secondary brand — hover states |
| `--color-brand-amber` | `#ffa110` | Tertiary — warm highlights |
| `--color-brand-gold` | `#ffd900` | Bright end of block gradient |
| `--color-text` | `#1f1f1f` | Primary text (Mistral Black, never #000) |
| `--color-text-secondary` | `hsl(0, 0%, 24%)` | Secondary text |
| `--color-text-muted` | `hsl(0, 0%, 50%)` | Muted/placeholder text |
| `--color-text-on-brand` | `#ffffff` | Text on orange/dark surfaces |
| `--color-border` | `hsl(240, 5.9%, 90%)` | Form borders (sole cool tone in the system) |
| `--color-success` | `#16a34a` | Connected, positive states |
| `--color-error` | `#dc2626` | Error states |
| `--color-dark` | `#1f1f1f` | Dark buttons, footer |

**Block Gradient (brand identity):**
`#ffd900` → `#ffe295` → `#ffa110` → `#ff8105` → `#fb6424` → `#fa520f`

### 1.2 Typography

Single font weight (400) everywhere. Hierarchy through size and color only — never weight variation.

| Token | Size | Line Height | Letter Spacing | Usage |
|-------|------|-------------|----------------|-------|
| `--text-display` | 48px / 3rem | 0.95 | -1.5px | Hero headings, large stat numbers |
| `--text-heading` | 32px / 2rem | 1.15 | normal | Page titles |
| `--text-subheading` | 24px / 1.5rem | 1.33 | normal | Section headings |
| `--text-card-title` | 18px / 1.125rem | 1.4 | normal | Card headings |
| `--text-body` | 16px / 1rem | 1.5 | normal | Body text, button text |
| `--text-caption` | 14px / 0.875rem | 1.43 | normal | Metadata, nav labels |
| `--text-small` | 12px / 0.75rem | 1.5 | normal | Badges, citations |

Font stack: `Arial, ui-sans-serif, system-ui, -apple-system, sans-serif`

Strategic `text-transform: uppercase` on CTA button labels only.

### 1.3 Spacing

Base unit: 8px

Scale: 4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px, 80px

Section vertical spacing: 48–80px between major sections.

### 1.4 Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-golden` | `rgba(127,99,21,0.12) -8px 16px 39px, rgba(127,99,21,0.1) -33px 64px 72px, rgba(127,99,21,0.06) -73px 144px 97px` | Elevated cards, detail panels, hero stats |
| `--shadow-card` | `rgba(127,99,21,0.08) -4px 8px 20px` | Standard cards |
| `--shadow-subtle` | `rgba(127,99,21,0.06) 0 2px 12px` | Nav bar, toolbars, input focus |

All shadows amber-tinted (rgb 127, 99, 21 base). Never gray or cool-toned shadows.

### 1.5 Border Radius

0px everywhere. Sharp, architectural corners on all elements. This creates intentional tension between soft warm colors and hard geometry.

---

## 2. Core Components

### 2.1 Navigation Bar

- Surface: `#ffffff` with `--shadow-subtle`
- Position: sticky top, full-width, ~56px height
- Layout: horizontal flex, space-between
- **Logo:** Block identity mark (4 vertical bars, 4px × 20px each, 2px gap) in gradient `#ffd900 → #ffa110 → #fb6424 → #fa520f`, followed by "OpenRaven" wordmark at 18px, weight 400, `#1f1f1f`, letter-spacing -0.5px
- **Nav links:** 14px, `hsl(0, 0%, 24%)`, mixed case (not uppercase)
- **Active link:** `#fa520f` text with 2px solid bottom border in `#fa520f`, 4px padding-bottom
- **Hover:** text color transitions to `#fa520f`

### 2.2 Buttons (shadcn/ui re-themed)

| Variant | Background | Text | Border | Notes |
|---------|-----------|------|--------|-------|
| Primary (dark solid) | `#1f1f1f` | `#ffffff` | none | Main CTAs |
| Secondary (cream) | `#fff0c2` | `#1f1f1f` | none | Warm secondary actions |
| Ghost | transparent | `#1f1f1f` (opacity 0.6) | none | Hover → opacity 1.0 |
| Destructive | `#dc2626` | `#ffffff` | none | Delete/remove actions |

All buttons: weight 400, 16px, 12px padding, 0 border-radius. CTA buttons use `text-transform: uppercase`.

### 2.3 Cards

- Surface: `#ffffff`, 0 radius, no visible border
- Standard elevation: `--shadow-card`
- Emphasized elevation: `--shadow-golden` (multi-layer)
- Body padding: 24px
- Optional warm header: `#fffaeb` or `#fff0c2` background section

### 2.4 Form Inputs (shadcn/ui re-themed)

- Background: `#ffffff`
- Border: 1px solid `hsl(240, 5.9%, 90%)` — the sole cool-toned element in the system
- Border radius: 0px
- Padding: 12px horizontal, 10px vertical
- Focus state: 2px ring in `#fa520f`
- Placeholder text: `hsl(0, 0%, 50%)`

### 2.5 Badges / Citations

- **Cream badge:** `#fff0c2` bg, `#1f1f1f` text, 0 radius
- **Source citation:** `#fffaeb` bg with 1px `#ffa110` border, 0 radius
- Font size: 12px (`--text-small`)

---

## 3. Page Designs

### 3.1 Ask Page (Chat Interface) — Route: `/`

**Layout:** Max-width 768px container, centered on warm ivory page bg.

**Chat Messages:**
- User bubbles: right-aligned, `linear-gradient(135deg, #fb6424, #fa520f)` bg, white text, 0 radius, max-width 75%
- Assistant bubbles: left-aligned, white surface, `--shadow-card` golden shadow, `#1f1f1f` text, 0 radius, max-width 85%
- Source citations: row of cream badges below assistant messages, 12px text

**Discovery Cards:**
- 2-column grid, white surface + `--shadow-golden`
- 4px colored left border per insight type:
  - Theme: `#fa520f` (orange)
  - Cluster: `#ffa110` (amber)
  - Gap: `#ffd900` (gold)
  - Trend: `#1f1f1f` (black)

**Input Area:**
- Fixed bottom, white surface with `--shadow-subtle`
- Full-width input field + dark solid send button

**Empty State:**
- 48px heading "What would you like to know?", `#1f1f1f`, weight 400, centered with generous 80px+ vertical whitespace

### 3.2 Ingest Page (File Upload) — Route: `/ingest`

**Layout:** Two sections — upload zone (top) + results (bottom).

**Upload Zone:**
- Large dashed border area: `#ffa110` dashes on `#fffaeb` bg, 200px min-height
- Centered icon + "Drop files here" at 24px
- Supported formats at 14px muted text
- Drag-over state: solid `#fa520f` border, intensified cream bg

**File List:**
- White cards with `--shadow-card`, each showing filename + type icon + processing status

**Results Summary:**
- 3-column stat grid: "Files Processed" / "Entities Extracted" / "Articles Generated"
- Large number at 48px display size (weight 400, tight tracking)
- Label at 14px caption below
- Warm ivory bg cards with `--shadow-golden`

### 3.3 Graph Page (Knowledge Graph) — Route: `/graph`

**Layout:** Full viewport height (`calc(100vh - 56px)`).

**Toolbar:**
- White surface strip at top with `--shadow-subtle`
- Search input (cool border, `#fa520f` focus ring)
- Type filter pills: cream bg (`#fff0c2`) toggles, `#fa520f` bg + white text when active
- Degree slider
- Export button (dark solid)

**Canvas:**
- Background: `#fef9ef` warm ivory (fully warm)
- Node colors (saturated for light bg):
  - Technology: `#fa520f` (orange)
  - Concept: `#1f1f1f` (black)
  - Person: `#ffa110` (amber)
  - Organization: `#d94800` (deep orange)
  - Event: `#b8860b` (dark goldenrod)
  - Location: `#8b6914` (warm brown)
- Edge color: `rgba(31, 31, 31, 0.15)` — subtle warm black
- Node labels: `#1f1f1f`, 12px
- Hover highlight: `#fa520f` ring, 3px stroke

**Detail Sidebar:**
- Slides from right, 320px width
- White surface with `--shadow-golden`
- Node name at 24px subheading
- Type badge (cream)
- Neighbor list as clickable cards with `--shadow-subtle`

### 3.4 Wiki Page (Knowledge Articles) — Route: `/wiki`

**Layout:** Two-column — sidebar (280px) + content area.

**Sidebar:**
- `#fffaeb` warm ivory background
- Article titles in list form
- Active article: white bg card with `--shadow-subtle`, 4px `#fa520f` left border
- Hover: cream bg (`#fff0c2`)

**Content Area:**
- White surface card with `--shadow-golden`, max-width 720px
- Article title: 32px heading
- Body: 16px, `#1f1f1f`, line-height 1.5
- Source references at bottom: cream badges
- Padding: 48px

### 3.5 Connectors Page (Integrations) — Route: `/connectors`

**Layout:** 2-column grid (`grid-cols-1 md:grid-cols-2`), gap 24px.

**Connector Cards:**
- White surface with `--shadow-card`
- Service icon area: 48px
- Service name: 18px card-title
- Description: 14px muted text
- Status badge:
  - Connected: cream bg with `#16a34a` text + green dot
  - Disconnected: ivory bg with muted text
- Connect button: dark solid (primary) when disconnected; cream (secondary) showing "Manage" when connected
- Sync results: expandable section with last sync stats on cream bg

### 3.6 Status Page (System Dashboard) — Route: `/status`

**Hero Stats Row:**
- 4-column grid at top
- Each stat: white card with `--shadow-golden`
- Large number: 48px display size, weight 400, tight letter-spacing
- Label: 14px muted text below
- Metrics: Total Files / Concepts / Connections / Topics

**LLM Info Card:**
- Full-width, cream bg (`#fff0c2`)
- Provider + model name at 18px
- Status dot (green when healthy)

**Top Topics:**
- List of topic cards, white surface, `--shadow-subtle`
- Topic name: 16px, document count as cream badge

**Health Insights:**
- White cards with `--shadow-card`, 4px colored left border:
  - Same color scheme as Discovery cards (orange/amber/gold/black)

---

## 4. Responsive Design

### Breakpoints

| Breakpoint | Width | Key Changes |
|-----------|-------|-------------|
| Mobile | <640px | Single column, nav collapses to hamburger, hero text → 32px |
| Tablet | 640–1024px | 2-column grids reduce to 1, sidebar collapses |
| Desktop | 1024px+ | Full layout, all columns, 48px display text |

### Scaling Rules

- Typography: display 48→32px, heading 32→24px, body stays 16px
- Navigation: horizontal → hamburger icon (3 horizontal bars, `#1f1f1f`), opens full-width dropdown with vertical nav links on cream bg (`#fff0c2`), slide-down animation
- Wiki sidebar: collapses to horizontal scrollable tab bar above content
- Graph sidebar: becomes bottom sheet (40% viewport height, drag-up to expand)
- Section spacing: 80px → 48px on mobile
- Warm ivory backgrounds maintained at all sizes

---

## 5. Migration Notes

### Files to Modify

| File | Changes |
|------|---------|
| `src/index.css` | Add CSS custom properties (design tokens), configure Tailwind theme |
| `src/App.tsx` | New nav layout with block identity logo, warm styling |
| `src/pages/AskPage.tsx` | Warm bubbles, golden shadow cards, new input area |
| `src/pages/IngestPage.tsx` | Warm upload zone, stat cards |
| `src/pages/GraphPage.tsx` | Warm toolbar, ivory canvas, new node colors, warm sidebar |
| `src/pages/WikiPage.tsx` | Warm sidebar, golden shadow content card |
| `src/pages/ConnectorsPage.tsx` | Warm connector cards, status badges |
| `src/pages/StatusPage.tsx` | Golden shadow stat cards, cream LLM card |
| `src/components/ChatMessage.tsx` | Gradient user bubbles, golden shadow assistant bubbles |
| `src/components/DiscoveryCard.tsx` | White cards with colored left borders, golden shadows |
| `src/components/FileUploader.tsx` | Warm dashed border zone |
| `src/components/GraphViewer.tsx` | Ivory canvas bg, new node colors, warm edges/labels |
| `src/components/GraphNodeDetail.tsx` | White panel with golden shadow |
| `src/components/SourceCitation.tsx` | Cream badges |

### New Files

| File | Purpose |
|------|---------|
| `src/design-tokens.css` | CSS custom properties for all tokens |
| `components.json` | shadcn/ui configuration |
| `src/components/ui/*` | shadcn/ui base components (button, input, card, badge, dialog) |
| `src/lib/utils.ts` | shadcn/ui utility (cn function) |

### Dependencies to Add

- `shadcn/ui` (via CLI init)
- `class-variance-authority` (shadcn dependency)
- `clsx` + `tailwind-merge` (shadcn dependency)

### What Does NOT Change

- Backend (Hono server, all routes)
- API contracts
- D3 force simulation logic (only colors/rendering change)
- React Router structure
- Test infrastructure
