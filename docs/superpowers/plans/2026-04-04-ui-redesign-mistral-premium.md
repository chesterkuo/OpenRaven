# Mistral Premium UI Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace OpenRaven's dark-mode UI with a warm, light-mode "Mistral Premium" design across all 6 pages.

**Architecture:** Add a CSS custom properties file for design tokens, install and re-theme shadcn/ui components (buttons, inputs, cards, badges) to the warm Mistral aesthetic, then systematically update each page and component to use the new tokens and warm color scheme. No backend or API changes.

**Tech Stack:** React 19, Tailwind CSS 4, shadcn/ui (re-themed), D3.js, Vite 6, Bun

**Spec:** `docs/superpowers/specs/2026-04-04-ui-redesign-mistral-premium-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `openraven-ui/src/design-tokens.css` | Create | CSS custom properties for all design tokens |
| `openraven-ui/src/index.css` | Modify | Import design tokens, configure Tailwind theme |
| `openraven-ui/src/lib/utils.ts` | Create | shadcn/ui `cn()` utility |
| `openraven-ui/src/components/ui/button.tsx` | Create | shadcn/ui Button re-themed to Mistral warm |
| `openraven-ui/src/components/ui/input.tsx` | Create | shadcn/ui Input re-themed to Mistral warm |
| `openraven-ui/src/components/ui/badge.tsx` | Create | shadcn/ui Badge re-themed to Mistral warm |
| `openraven-ui/src/components/ui/card.tsx` | Create | shadcn/ui Card re-themed to Mistral warm |
| `openraven-ui/src/App.tsx` | Modify | New warm nav with block identity logo |
| `openraven-ui/src/components/ChatMessage.tsx` | Modify | Gradient user bubbles, golden shadow assistant |
| `openraven-ui/src/components/SourceCitation.tsx` | Modify | Cream badges with amber border |
| `openraven-ui/src/components/DiscoveryCard.tsx` | Modify | White cards with colored left borders |
| `openraven-ui/src/components/FileUploader.tsx` | Modify | Warm dashed border upload zone |
| `openraven-ui/src/pages/AskPage.tsx` | Modify | Warm chat layout, fixed input bar |
| `openraven-ui/src/pages/IngestPage.tsx` | Modify | Warm upload page, stat cards |
| `openraven-ui/src/pages/StatusPage.tsx` | Modify | Golden shadow stat cards, cream LLM card |
| `openraven-ui/src/pages/WikiPage.tsx` | Modify | Warm sidebar, golden shadow content |
| `openraven-ui/src/pages/ConnectorsPage.tsx` | Modify | Warm connector cards, status badges |
| `openraven-ui/src/pages/GraphPage.tsx` | Modify | Warm toolbar, ivory canvas setup |
| `openraven-ui/src/components/GraphViewer.tsx` | Modify | Ivory canvas, warm node colors, warm edges |
| `openraven-ui/src/components/GraphNodeDetail.tsx` | Modify | White panel with golden shadow |
| `openraven-ui/package.json` | Modify | Add shadcn dependencies |

---

### Task 1: Install shadcn/ui Dependencies

**Files:**
- Modify: `openraven-ui/package.json`

- [ ] **Step 1: Install dependencies**

```bash
cd openraven-ui && bun add clsx tailwind-merge class-variance-authority
```

- [ ] **Step 2: Verify installation**

```bash
cd openraven-ui && bun run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
cd openraven-ui && git add package.json bun.lockb
git commit -m "chore: add shadcn/ui dependencies (cva, clsx, tailwind-merge)"
```

---

### Task 2: Create Design Tokens + Utility Files

**Files:**
- Create: `openraven-ui/src/design-tokens.css`
- Modify: `openraven-ui/src/index.css`
- Create: `openraven-ui/src/lib/utils.ts`

- [ ] **Step 1: Create design tokens CSS file**

Create `openraven-ui/src/design-tokens.css`:

```css
:root {
  /* Backgrounds */
  --bg-page: #fef9ef;
  --bg-surface: #ffffff;
  --bg-surface-warm: #fff0c2;
  --bg-surface-hover: #fffaeb;

  /* Brand */
  --color-brand: #fa520f;
  --color-brand-flame: #fb6424;
  --color-brand-amber: #ffa110;
  --color-brand-gold: #ffd900;

  /* Text */
  --color-text: #1f1f1f;
  --color-text-secondary: hsl(0, 0%, 24%);
  --color-text-muted: hsl(0, 0%, 50%);
  --color-text-on-brand: #ffffff;

  /* Borders */
  --color-border: hsl(240, 5.9%, 90%);

  /* Functional */
  --color-success: #16a34a;
  --color-error: #dc2626;
  --color-dark: #1f1f1f;

  /* Shadows */
  --shadow-golden: rgba(127,99,21,0.12) -8px 16px 39px,
                    rgba(127,99,21,0.1) -33px 64px 72px,
                    rgba(127,99,21,0.06) -73px 144px 97px;
  --shadow-card: rgba(127,99,21,0.08) -4px 8px 20px;
  --shadow-subtle: rgba(127,99,21,0.06) 0 2px 12px;

  /* Typography */
  --font-family: Arial, ui-sans-serif, system-ui, -apple-system, sans-serif;

  /* Graph node colors */
  --node-technology: #fa520f;
  --node-concept: #1f1f1f;
  --node-person: #ffa110;
  --node-organization: #d94800;
  --node-event: #b8860b;
  --node-location: #8b6914;
}
```

- [ ] **Step 2: Update index.css to import tokens and set base styles**

Replace the content of `openraven-ui/src/index.css` with:

```css
@import "tailwindcss";
@import "./design-tokens.css";

* {
  border-color: var(--color-border);
}

body {
  font-family: var(--font-family);
  background-color: var(--bg-page);
  color: var(--color-text);
  font-weight: 400;
}
```

- [ ] **Step 3: Create cn() utility**

Create `openraven-ui/src/lib/utils.ts`:

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 4: Verify build**

```bash
cd openraven-ui && bun run build
```

Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
cd openraven-ui && git add src/design-tokens.css src/index.css src/lib/utils.ts
git commit -m "feat(ui): add Mistral Premium design tokens and cn() utility"
```

---

### Task 3: Create shadcn/ui Base Components

**Files:**
- Create: `openraven-ui/src/components/ui/button.tsx`
- Create: `openraven-ui/src/components/ui/input.tsx`
- Create: `openraven-ui/src/components/ui/badge.tsx`
- Create: `openraven-ui/src/components/ui/card.tsx`

- [ ] **Step 1: Create Button component**

Create `openraven-ui/src/components/ui/button.tsx`:

```tsx
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center text-base font-normal transition-colors disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-[var(--color-dark)] text-[var(--color-text-on-brand)] hover:bg-[#333333]",
        secondary: "bg-[var(--bg-surface-warm)] text-[var(--color-text)] hover:bg-[var(--bg-surface-hover)]",
        ghost: "text-[var(--color-text)] opacity-60 hover:opacity-100",
        destructive: "bg-[var(--color-error)] text-[var(--color-text-on-brand)] hover:bg-red-700",
      },
      size: {
        default: "px-3 py-1.5 text-sm",
        lg: "px-5 py-2.5 text-base",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}
```

- [ ] **Step 2: Create Input component**

Create `openraven-ui/src/components/ui/input.tsx`:

```tsx
import { cn } from "@/lib/utils";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={cn(
        "bg-[var(--bg-surface)] border border-[var(--color-border)] px-3 py-2.5 text-base text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]",
        className
      )}
      {...props}
    />
  );
}
```

- [ ] **Step 3: Create Badge component**

Create `openraven-ui/src/components/ui/badge.tsx`:

```tsx
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center text-xs font-normal",
  {
    variants: {
      variant: {
        default: "bg-[var(--bg-surface-warm)] text-[var(--color-text)] px-2 py-0.5",
        citation: "bg-[var(--bg-surface-hover)] border border-[var(--color-brand-amber)] text-[var(--color-text)] px-1.5 py-0.5",
        status: "px-2 py-0.5",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant, className }))} {...props} />;
}
```

- [ ] **Step 4: Create Card component**

Create `openraven-ui/src/components/ui/card.tsx`:

```tsx
import { cn } from "@/lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  elevated?: boolean;
}

export function Card({ className, elevated, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "bg-[var(--bg-surface)] p-6",
        className
      )}
      style={{ boxShadow: elevated ? "var(--shadow-golden)" : "var(--shadow-card)" }}
      {...props}
    />
  );
}
```

- [ ] **Step 5: Verify build**

```bash
cd openraven-ui && bun run build
```

Expected: Build succeeds.

- [ ] **Step 6: Commit**

```bash
cd openraven-ui && git add src/components/ui/
git commit -m "feat(ui): add shadcn-style base components (Button, Input, Badge, Card)"
```

---

### Task 4: Redesign App Shell + Navigation

**Files:**
- Modify: `openraven-ui/src/App.tsx`

- [ ] **Step 1: Replace App.tsx with warm nav and block identity logo**

Replace the full content of `openraven-ui/src/App.tsx` with:

```tsx
import { Routes, Route, NavLink, useLocation } from "react-router-dom";
import AskPage from "./pages/AskPage";
import StatusPage from "./pages/StatusPage";
import IngestPage from "./pages/IngestPage";
import GraphPage from "./pages/GraphPage";
import WikiPage from "./pages/WikiPage";
import ConnectorsPage from "./pages/ConnectorsPage";

function BlockLogo() {
  return (
    <div className="flex gap-0.5">
      <div className="w-1 h-5" style={{ background: "#ffd900" }} />
      <div className="w-1 h-5" style={{ background: "#ffa110" }} />
      <div className="w-1 h-5" style={{ background: "#fb6424" }} />
      <div className="w-1 h-5" style={{ background: "#fa520f" }} />
    </div>
  );
}

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  isActive
    ? "text-[var(--color-brand)] border-b-2 border-[var(--color-brand)] pb-1 text-sm"
    : "text-[var(--color-text-secondary)] hover:text-[var(--color-brand)] text-sm pb-1";

export default function App() {
  const location = useLocation();
  const isGraphPage = location.pathname === "/graph";

  return (
    <div className="h-screen flex flex-col" style={{ background: "var(--bg-page)", color: "var(--color-text)" }}>
      <nav
        className="px-6 py-3 flex items-center gap-6 shrink-0 sticky top-0 z-50"
        style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-subtle)" }}
      >
        <div className="flex items-center gap-2">
          <BlockLogo />
          <span className="text-lg tracking-tight" style={{ color: "var(--color-text)", letterSpacing: "-0.5px" }}>
            OpenRaven
          </span>
        </div>
        <NavLink to="/" end className={navLinkClass}>Ask</NavLink>
        <NavLink to="/ingest" className={navLinkClass}>Add Files</NavLink>
        <NavLink to="/graph" className={navLinkClass}>Graph</NavLink>
        <NavLink to="/wiki" className={navLinkClass}>Wiki</NavLink>
        <NavLink to="/connectors" className={navLinkClass}>Connectors</NavLink>
        <NavLink to="/status" className={navLinkClass}>Status</NavLink>
      </nav>
      <main className={isGraphPage ? "flex-1 flex flex-col min-h-0" : "max-w-4xl mx-auto px-6 py-8 w-full flex-1"}>
        <Routes>
          <Route path="/" element={<AskPage />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/wiki" element={<WikiPage />} />
          <Route path="/connectors" element={<ConnectorsPage />} />
          <Route path="/status" element={<StatusPage />} />
        </Routes>
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd openraven-ui && bun run build
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
cd openraven-ui && git add src/App.tsx
git commit -m "feat(ui): redesign nav with Mistral block identity logo and warm styling"
```

---

### Task 5: Redesign Chat Components (ChatMessage, SourceCitation, DiscoveryCard)

**Files:**
- Modify: `openraven-ui/src/components/ChatMessage.tsx`
- Modify: `openraven-ui/src/components/SourceCitation.tsx`
- Modify: `openraven-ui/src/components/DiscoveryCard.tsx`

- [ ] **Step 1: Update SourceCitation to warm cream badge**

Replace the full content of `openraven-ui/src/components/SourceCitation.tsx` with:

```tsx
interface Props { document: string; excerpt: string; charStart?: number; charEnd?: number; }

export default function SourceCitation({ document, excerpt, charStart, charEnd }: Props) {
  const location = charStart != null && charEnd != null ? ` (chars ${charStart}-${charEnd})` : "";
  return (
    <span
      className="inline-flex items-center gap-1 text-xs cursor-help mx-0.5 px-1.5 py-0.5"
      style={{
        background: "var(--bg-surface-hover)",
        border: "1px solid var(--color-brand-amber)",
        color: "var(--color-text)",
      }}
      title={`${document}${location}\n${excerpt}`}
    >
      {document}
    </span>
  );
}
```

- [ ] **Step 2: Update ChatMessage to warm bubbles**

Replace the full content of `openraven-ui/src/components/ChatMessage.tsx` with:

```tsx
import SourceCitation from "./SourceCitation";

interface Props { role: "user" | "assistant"; content: string; }

function renderContentWithCitations(content: string) {
  const sourcePattern = /\[Source:\s*([^\]]+?)(?::(\d+)-(\d+))?\]/g;
  const parts: (string | { document: string; charStart?: number; charEnd?: number })[] = [];
  let lastIndex = 0;
  for (const match of content.matchAll(sourcePattern)) {
    if (match.index! > lastIndex) parts.push(content.slice(lastIndex, match.index!));
    parts.push({ document: match[1].trim(), charStart: match[2] ? Number(match[2]) : undefined, charEnd: match[3] ? Number(match[3]) : undefined });
    lastIndex = match.index! + match[0].length;
  }
  if (lastIndex < content.length) parts.push(content.slice(lastIndex));
  return parts.map((part, i) => typeof part === "string" ? <span key={i}>{part}</span> : <SourceCitation key={i} document={part.document} excerpt="" charStart={part.charStart} charEnd={part.charEnd} />);
}

export default function ChatMessage({ role, content }: Props) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className="max-w-[80%] px-4 py-2.5 text-sm leading-relaxed"
        style={isUser
          ? { background: "linear-gradient(135deg, #fb6424, #fa520f)", color: "var(--color-text-on-brand)" }
          : { background: "var(--bg-surface)", color: "var(--color-text)", boxShadow: "var(--shadow-card)" }
        }
      >
        <div className="whitespace-pre-wrap">{isUser ? content : renderContentWithCitations(content)}</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Update DiscoveryCard to warm design with colored left borders**

Replace the full content of `openraven-ui/src/components/DiscoveryCard.tsx` with:

```tsx
interface Insight { insight_type: string; title: string; description: string; related_entities: string[]; }
interface Props { insight: Insight; }

const TYPE_BORDERS: Record<string, string> = {
  theme: "#fa520f",
  cluster: "#ffa110",
  gap: "#ffd900",
  trend: "#1f1f1f",
};

export default function DiscoveryCard({ insight }: Props) {
  const borderColor = TYPE_BORDERS[insight.insight_type] ?? TYPE_BORDERS.theme;
  return (
    <div
      className="p-4"
      style={{
        background: "var(--bg-surface)",
        boxShadow: "var(--shadow-golden)",
        borderLeft: `4px solid ${borderColor}`,
      }}
    >
      <span className="text-xs uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>
        {insight.insight_type}
      </span>
      <h3 className="text-base" style={{ color: "var(--color-text)" }}>{insight.title}</h3>
      <p className="text-sm mt-1" style={{ color: "var(--color-text-secondary)" }}>{insight.description}</p>
      {insight.related_entities.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {insight.related_entities.slice(0, 5).map(entity => (
            <span key={entity} className="text-xs px-2 py-0.5" style={{ background: "var(--bg-surface-warm)", color: "var(--color-text)" }}>
              {entity}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Verify build**

```bash
cd openraven-ui && bun run build
```

Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
cd openraven-ui && git add src/components/ChatMessage.tsx src/components/SourceCitation.tsx src/components/DiscoveryCard.tsx
git commit -m "feat(ui): redesign chat components with warm Mistral Premium styling"
```

---

### Task 6: Redesign FileUploader Component

**Files:**
- Modify: `openraven-ui/src/components/FileUploader.tsx`

- [ ] **Step 1: Update FileUploader to warm dashed border design**

Replace the full content of `openraven-ui/src/components/FileUploader.tsx` with:

```tsx
import { useCallback } from "react";

interface Props { onUpload: (files: File[]) => void; disabled?: boolean; }

export default function FileUploader({ onUpload, disabled }: Props) {
  const handleDrop = useCallback((e: React.DragEvent) => { e.preventDefault(); if (disabled) return; const files = Array.from(e.dataTransfer.files); if (files.length > 0) onUpload(files); }, [onUpload, disabled]);
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => { const files = Array.from(e.target.files ?? []); if (files.length > 0) onUpload(files); }, [onUpload]);

  return (
    <div
      onDrop={handleDrop}
      onDragOver={e => e.preventDefault()}
      className="p-12 text-center transition-colors"
      style={{
        border: `2px dashed ${disabled ? "var(--color-border)" : "var(--color-brand-amber)"}`,
        background: disabled ? "var(--bg-surface)" : "var(--bg-surface-hover)",
        color: disabled ? "var(--color-text-muted)" : "var(--color-text-secondary)",
        cursor: disabled ? "default" : "pointer",
        minHeight: "200px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <p className="text-2xl mb-2" style={{ color: disabled ? "var(--color-text-muted)" : "var(--color-text)" }}>
        Drop files here
      </p>
      <p className="text-sm mb-4" style={{ color: "var(--color-text-muted)" }}>
        PDF, DOCX, PPTX, XLSX, Markdown, TXT
      </p>
      <label
        className="inline-block px-4 py-2 text-sm cursor-pointer"
        style={{
          background: disabled ? "var(--color-border)" : "var(--color-dark)",
          color: disabled ? "var(--color-text-muted)" : "var(--color-text-on-brand)",
        }}
      >
        BROWSE FILES
        <input type="file" multiple onChange={handleChange} disabled={disabled} className="hidden" accept=".pdf,.docx,.pptx,.xlsx,.md,.txt,.html" />
      </label>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd openraven-ui && bun run build
```

- [ ] **Step 3: Commit**

```bash
cd openraven-ui && git add src/components/FileUploader.tsx
git commit -m "feat(ui): redesign FileUploader with warm dashed border zone"
```

---

### Task 7: Redesign AskPage

**Files:**
- Modify: `openraven-ui/src/pages/AskPage.tsx`

- [ ] **Step 1: Update AskPage to warm design**

Replace the full content of `openraven-ui/src/pages/AskPage.tsx` with:

```tsx
import { useState, useRef, useEffect } from "react";
import ChatMessage from "../components/ChatMessage";
import DiscoveryCard from "../components/DiscoveryCard";

interface SourceRef { document: string; excerpt: string; char_start: number; char_end: number; }
interface Message { role: "user" | "assistant"; content: string; sources?: SourceRef[]; }
interface Insight { insight_type: string; title: string; description: string; related_entities: string[]; }

export default function AskPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState<Insight[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { fetch("/api/discovery").then(r => r.json()).then(setInsights).catch(() => {}); }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: question }]);
    setLoading(true);
    try {
      const res = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, mode: "mix" }) });
      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.answer, sources: data.sources ?? [] }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Error: Could not reach the knowledge engine." }]);
    } finally { setLoading(false); }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {messages.length === 0 && insights.length === 0 && (
        <div className="flex-1 flex items-center justify-center">
          <h2 className="text-5xl" style={{ color: "var(--color-text)", letterSpacing: "-1.5px", lineHeight: 0.95 }}>
            What would you like to know?
          </h2>
        </div>
      )}
      {messages.length === 0 && insights.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm mb-3" style={{ color: "var(--color-text-muted)" }}>Discoveries from your knowledge base</h2>
          <div className="grid grid-cols-2 gap-4">{insights.map((insight, i) => <DiscoveryCard key={i} insight={insight} />)}</div>
        </div>
      )}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.map((msg, i) => (
          <div key={i}>
            <ChatMessage role={msg.role} content={msg.content} />
            {msg.sources && msg.sources.length > 0 && (
              <div className="ml-4 mt-1 mb-2 pl-3" style={{ borderLeft: "2px solid var(--color-border)" }}>
                <div className="text-xs mb-1" style={{ color: "var(--color-text-muted)" }}>Sources ({msg.sources.length})</div>
                {msg.sources.map((s, j) => (
                  <div key={j} className="text-xs mb-0.5" style={{ color: "var(--color-text-secondary)" }}>
                    <span style={{ color: "var(--color-brand)" }}>{s.document}</span>
                    {s.excerpt && <span className="ml-2" style={{ color: "var(--color-text-muted)" }}>— {s.excerpt}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="text-sm animate-pulse" style={{ color: "var(--color-text-muted)" }}>Thinking...</div>}
        <div ref={bottomRef} />
      </div>
      <form
        onSubmit={handleSubmit}
        className="flex gap-3 pt-4"
        style={{ borderTop: "1px solid var(--color-border)" }}
      >
        <input
          type="text" value={input} onChange={e => setInput(e.target.value)}
          placeholder="Ask your knowledge base..."
          className="flex-1 px-4 py-2.5 focus:outline-none focus:ring-2"
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--color-border)",
            color: "var(--color-text)",
            focusRingColor: "var(--color-brand)",
          }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-5 py-2.5 text-sm uppercase transition-colors disabled:opacity-50"
          style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
        >
          Ask
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd openraven-ui && bun run build
```

- [ ] **Step 3: Commit**

```bash
cd openraven-ui && git add src/pages/AskPage.tsx
git commit -m "feat(ui): redesign AskPage with warm chat layout and empty state"
```

---

### Task 8: Redesign IngestPage

**Files:**
- Modify: `openraven-ui/src/pages/IngestPage.tsx`

- [ ] **Step 1: Update IngestPage to warm design**

Replace the full content of `openraven-ui/src/pages/IngestPage.tsx` with:

```tsx
import { useState } from "react";
import FileUploader from "../components/FileUploader";

interface IngestResult { files_processed: number; entities_extracted: number; articles_generated: number; errors: string[]; }

const STAGE_LABELS: Record<string, string> = {
  uploading: "Uploading files...",
  processing: "Processing documents...",
  done: "Complete",
  error: "Error occurred",
};

export default function IngestPage() {
  const [result, setResult] = useState<IngestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState<string | null>(null);

  async function handleUpload(files: File[]) {
    setLoading(true); setResult(null); setStage("uploading");
    const formData = new FormData();
    for (const file of files) formData.append("files", file);
    try {
      setStage("processing");
      const res = await fetch("/api/ingest", { method: "POST", body: formData });
      const data = await res.json();
      setResult(data);
      setStage("done");
    } catch {
      setResult({ files_processed: 0, entities_extracted: 0, articles_generated: 0, errors: ["Failed to connect to the knowledge engine."] });
      setStage("error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-3xl mb-6" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>Add Documents</h1>
      <FileUploader onUpload={handleUpload} disabled={loading} />
      {loading && stage && (
        <div className="mt-6">
          <div className="flex items-center gap-3">
            <div className="w-4 h-4 border-2 border-t-transparent animate-spin" style={{ borderColor: "var(--color-brand)", borderTopColor: "transparent" }} />
            <span style={{ color: "var(--color-text-secondary)" }}>{STAGE_LABELS[stage] ?? stage}</span>
          </div>
          <div className="mt-2 h-1 overflow-hidden" style={{ background: "var(--color-border)" }}>
            <div className="h-full animate-pulse" style={{ background: "var(--color-brand)", width: stage === "processing" ? "60%" : "20%" }} />
          </div>
        </div>
      )}
      {result && !loading && (
        <div className="mt-8 grid grid-cols-3 gap-6 text-center">
          {[
            { label: "Files processed", value: result.files_processed },
            { label: "Entities extracted", value: result.entities_extracted },
            { label: "Articles generated", value: result.articles_generated },
          ].map(stat => (
            <div key={stat.label} className="p-6" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)" }}>
              <div className="text-5xl" style={{ color: "var(--color-text)", letterSpacing: "-1.5px", lineHeight: 0.95 }}>
                {stat.value}
              </div>
              <div className="text-sm mt-2" style={{ color: "var(--color-text-muted)" }}>{stat.label}</div>
            </div>
          ))}
          {result.errors.length > 0 && (
            <div className="col-span-3 text-sm" style={{ color: "var(--color-error)" }}>
              {result.errors.map((e, i) => <div key={i}>{e}</div>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify build and commit**

```bash
cd openraven-ui && bun run build && git add src/pages/IngestPage.tsx && git commit -m "feat(ui): redesign IngestPage with warm upload zone and stat cards"
```

---

### Task 9: Redesign StatusPage

**Files:**
- Modify: `openraven-ui/src/pages/StatusPage.tsx`

- [ ] **Step 1: Update StatusPage to warm design with golden shadow stat cards**

Replace the full content of `openraven-ui/src/pages/StatusPage.tsx` with:

```tsx
import { useEffect, useState } from "react";

interface Status { total_files: number; total_entities: number; total_connections: number; topic_count: number; top_topics: string[]; confidence_avg: number; }

export default function StatusPage() {
  const [status, setStatus] = useState<Status | null>(null);
  useEffect(() => { fetch("/api/status").then(r => r.json()).then(setStatus).catch(() => {}); }, []);

  const [provider, setProvider] = useState<{provider: string; llm_model: string} | null>(null);
  useEffect(() => { fetch("/api/config/provider").then(r => r.json()).then(setProvider).catch(() => {}); }, []);

  const [insights, setInsights] = useState<{insight_type: string; title: string; description: string; severity: string}[]>([]);
  useEffect(() => { fetch("/api/health/insights").then(r => r.json()).then(setInsights).catch(() => {}); }, []);

  if (!status) return <div style={{ color: "var(--color-text-muted)" }}>Loading...</div>;

  const BORDER_COLORS: Record<string, string> = {
    warning: "var(--color-brand-amber)",
    critical: "var(--color-error)",
    info: "var(--color-brand)",
  };

  return (
    <div>
      <h1 className="text-3xl mb-6" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>Knowledge Base Status</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
        {[
          { label: "Files", value: status.total_files },
          { label: "Concepts", value: status.total_entities },
          { label: "Connections", value: status.total_connections },
          { label: "Topics", value: status.topic_count },
        ].map(stat => (
          <div key={stat.label} className="p-4 text-center" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)" }}>
            <div className="text-5xl" style={{ color: "var(--color-text)", letterSpacing: "-1.5px", lineHeight: 0.95 }}>
              {stat.value}
            </div>
            <div className="text-sm mt-2" style={{ color: "var(--color-text-muted)" }}>{stat.label}</div>
          </div>
        ))}
      </div>
      {provider && (
        <div className="mb-8 p-4" style={{ background: "var(--bg-surface-warm)" }}>
          <span className="text-sm" style={{ color: "var(--color-text-muted)" }}>LLM: </span>
          <span className="text-sm" style={{ color: "var(--color-text)" }}>
            {provider.provider}/{provider.llm_model}
          </span>
          <span className="inline-block w-2 h-2 ml-2" style={{ background: "var(--color-success)", borderRadius: "50%" }} />
        </div>
      )}
      {status.top_topics.length > 0 && (
        <div className="mb-6">
          <h2 className="text-2xl mb-3" style={{ color: "var(--color-text)", lineHeight: 1.33 }}>Top Topics</h2>
          <div className="flex flex-wrap gap-2">
            {status.top_topics.map(topic => (
              <span key={topic} className="px-3 py-1 text-sm" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-subtle)", color: "var(--color-text)" }}>
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}
      {insights.length > 0 && (
        <div className="mt-6">
          <h2 className="text-2xl mb-3" style={{ color: "var(--color-text)", lineHeight: 1.33 }}>Health Insights</h2>
          <div className="flex flex-col gap-3">
            {insights.map((insight, i) => (
              <div
                key={i}
                className="p-4 text-sm"
                style={{
                  background: "var(--bg-surface)",
                  boxShadow: "var(--shadow-card)",
                  borderLeft: `4px solid ${BORDER_COLORS[insight.severity] ?? "var(--color-brand)"}`,
                }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs uppercase" style={{ color: "var(--color-text-muted)" }}>{insight.insight_type}</span>
                  <span style={{ color: "var(--color-text)" }}>{insight.title}</span>
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>{insight.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify build and commit**

```bash
cd openraven-ui && bun run build && git add src/pages/StatusPage.tsx && git commit -m "feat(ui): redesign StatusPage with golden shadow stat cards"
```

---

### Task 10: Redesign WikiPage

**Files:**
- Modify: `openraven-ui/src/pages/WikiPage.tsx`

- [ ] **Step 1: Update WikiPage to warm two-column design**

Replace the full content of `openraven-ui/src/pages/WikiPage.tsx` with:

```tsx
import { useEffect, useState } from "react";

interface WikiListItem { slug: string; title: string; }
interface WikiArticle { slug: string; title: string; content: string; }

export default function WikiPage() {
  const [articles, setArticles] = useState<WikiListItem[]>([]);
  const [selected, setSelected] = useState<WikiArticle | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/wiki").then(r => r.json()).then(setArticles).catch(() => {}).finally(() => setLoading(false));
  }, []);

  async function loadArticle(slug: string) {
    const res = await fetch(`/api/wiki/${encodeURIComponent(slug)}`);
    if (res.ok) setSelected(await res.json());
  }

  if (loading) return <div style={{ color: "var(--color-text-muted)" }}>Loading wiki...</div>;

  if (articles.length === 0) {
    return (
      <div>
        <h1 className="text-3xl mb-2" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>Knowledge Wiki</h1>
        <p style={{ color: "var(--color-text-muted)" }}>No articles yet. Add files to start generating wiki articles.</p>
      </div>
    );
  }

  return (
    <div className="flex gap-6">
      <div className="w-70 shrink-0" style={{ background: "var(--bg-surface-hover)" }}>
        <div className="flex items-center justify-between p-4">
          <h2 className="text-lg" style={{ color: "var(--color-text)" }}>Articles ({articles.length})</h2>
          <a
            href="/api/wiki/export"
            download
            className="text-xs px-3 py-1 uppercase"
            style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
          >
            Export
          </a>
        </div>
        <div className="flex flex-col">
          {articles.map((a) => (
            <button
              key={a.slug}
              onClick={() => loadArticle(a.slug)}
              className="text-left text-sm px-4 py-2 truncate transition-colors"
              style={selected?.slug === a.slug
                ? { background: "var(--bg-surface)", boxShadow: "var(--shadow-subtle)", borderLeft: "4px solid var(--color-brand)", color: "var(--color-text)" }
                : { color: "var(--color-text-secondary)", borderLeft: "4px solid transparent" }
              }
              onMouseEnter={e => { if (selected?.slug !== a.slug) (e.target as HTMLElement).style.background = "var(--bg-surface-warm)"; }}
              onMouseLeave={e => { if (selected?.slug !== a.slug) (e.target as HTMLElement).style.background = "transparent"; }}
            >
              {a.title}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 min-w-0">
        {selected ? (
          <div className="p-12" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)", maxWidth: "720px" }}>
            <h1 className="text-3xl mb-6" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>{selected.title}</h1>
            <div className="whitespace-pre-wrap text-base leading-relaxed" style={{ color: "var(--color-text)" }}>
              {selected.content}
            </div>
          </div>
        ) : (
          <div className="text-sm" style={{ color: "var(--color-text-muted)" }}>Select an article to read</div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build and commit**

```bash
cd openraven-ui && bun run build && git add src/pages/WikiPage.tsx && git commit -m "feat(ui): redesign WikiPage with warm sidebar and golden shadow content"
```

---

### Task 11: Redesign ConnectorsPage

**Files:**
- Modify: `openraven-ui/src/pages/ConnectorsPage.tsx`

- [ ] **Step 1: Update ConnectorsPage to warm card design**

Replace the full content of `openraven-ui/src/pages/ConnectorsPage.tsx` with:

```tsx
import { useEffect, useState } from "react";

interface ConnectorStatus {
  gdrive: { connected: boolean };
  gmail: { connected: boolean };
  meet: { connected: boolean };
  otter: { connected: boolean };
  google_configured: boolean;
}

interface SyncResult {
  files_synced: number;
  entities_extracted: number;
  articles_generated: number;
  errors: string[];
}

export default function ConnectorsPage() {
  const [status, setStatus] = useState<ConnectorStatus | null>(null);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [result, setResult] = useState<SyncResult | null>(null);
  const [otterKey, setOtterKey] = useState("");
  const [savingKey, setSavingKey] = useState(false);

  useEffect(() => {
    fetch("/api/connectors/status").then(r => r.json()).then(setStatus).catch(() => {});
  }, []);

  async function handleConnect() {
    const res = await fetch("/api/connectors/google/auth-url");
    const data = await res.json();
    if (data.auth_url) {
      window.open(data.auth_url, "_blank", "width=500,height=600");
      const poll = setInterval(async () => {
        try {
          const statusRes = await fetch("/api/connectors/status");
          const statusData = await statusRes.json();
          if (statusData.gdrive?.connected) {
            clearInterval(poll);
            setStatus(statusData);
          }
        } catch { /* ignore polling errors */ }
      }, 2000);
      setTimeout(() => clearInterval(poll), 120_000);
    }
  }

  async function handleSaveOtterKey() {
    if (!otterKey.trim()) return;
    setSavingKey(true);
    try {
      await fetch("/api/connectors/otter/save-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: otterKey.trim() }),
      });
      const statusRes = await fetch("/api/connectors/status");
      setStatus(await statusRes.json());
      setOtterKey("");
    } catch { /* ignore */ }
    finally { setSavingKey(false); }
  }

  async function handleSync(connector: "gdrive" | "gmail" | "meet" | "otter") {
    setSyncing(connector);
    setResult(null);
    try {
      const res = await fetch(`/api/connectors/${connector}/sync`, { method: "POST" });
      setResult(await res.json());
    } catch {
      setResult({ files_synced: 0, entities_extracted: 0, articles_generated: 0, errors: ["Sync failed"] });
    } finally {
      setSyncing(null);
    }
  }

  if (!status) return <div style={{ color: "var(--color-text-muted)" }}>Loading...</div>;

  const connectorBtn = (connected: boolean, connector: string, label: string) => {
    if (!connected) {
      return (
        <button
          onClick={handleConnect}
          disabled={!status.google_configured}
          className="text-sm px-3 py-1.5 uppercase disabled:opacity-50"
          style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
        >
          Connect
        </button>
      );
    }
    return (
      <button
        onClick={() => handleSync(connector as "gdrive" | "gmail" | "meet" | "otter")}
        disabled={syncing !== null}
        className="text-sm px-3 py-1.5 uppercase disabled:opacity-50"
        style={{ background: "var(--bg-surface-warm)", color: "var(--color-text)" }}
      >
        {syncing === connector ? "Syncing..." : label}
      </button>
    );
  };

  const statusBadge = (connected: boolean) => (
    <span
      className="text-xs px-2 py-0.5 flex items-center gap-1.5"
      style={{
        background: connected ? "var(--bg-surface-warm)" : "var(--bg-surface-hover)",
        color: connected ? "var(--color-success)" : "var(--color-text-muted)",
      }}
    >
      {connected && <span className="inline-block w-1.5 h-1.5" style={{ background: "var(--color-success)", borderRadius: "50%" }} />}
      {connected ? "Connected" : "Not connected"}
    </span>
  );

  const connectors = [
    { key: "gdrive", name: "Google Drive", desc: "Import documents from your Google Drive (PDF, Docs, Sheets, Slides).", connected: status.gdrive.connected, syncLabel: "Sync Now" },
    { key: "gmail", name: "Gmail", desc: "Import emails from your Gmail account as knowledge base entries.", connected: status.gmail.connected, syncLabel: "Sync Now" },
    { key: "meet", name: "Google Meet", desc: "Import meeting transcripts from Google Meet.", connected: status.meet.connected, syncLabel: "Sync Transcripts" },
  ];

  return (
    <div>
      <h1 className="text-3xl mb-6" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>Connectors</h1>

      {!status.google_configured && (
        <div className="p-4 mb-6 text-sm" style={{ background: "var(--bg-surface-warm)", borderLeft: "4px solid var(--color-brand-amber)", color: "var(--color-text)" }}>
          Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env to enable connectors.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {connectors.map(c => (
          <div key={c.key} className="p-4" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-card)" }}>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg" style={{ color: "var(--color-text)" }}>{c.name}</h2>
              {statusBadge(c.connected)}
            </div>
            <p className="text-sm mb-3" style={{ color: "var(--color-text-muted)" }}>{c.desc}</p>
            {connectorBtn(c.connected, c.key, c.syncLabel)}
          </div>
        ))}

        {/* Otter.ai */}
        <div className="p-4" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-card)" }}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg" style={{ color: "var(--color-text)" }}>Otter.ai</h2>
            {statusBadge(status.otter.connected)}
          </div>
          <p className="text-sm mb-3" style={{ color: "var(--color-text-muted)" }}>Import meeting transcripts from Otter.ai.</p>
          {!status.otter.connected ? (
            <div className="flex gap-2">
              <input
                type="password"
                value={otterKey}
                onChange={(e) => setOtterKey(e.target.value)}
                placeholder="Otter.ai API key"
                className="flex-1 px-2 py-1.5 text-sm focus:outline-none focus:ring-2"
                style={{
                  background: "var(--bg-surface)",
                  border: "1px solid var(--color-border)",
                  color: "var(--color-text)",
                  focusRingColor: "var(--color-brand)",
                }}
              />
              <button
                onClick={handleSaveOtterKey}
                disabled={savingKey || !otterKey.trim()}
                className="text-sm px-3 py-1.5 uppercase disabled:opacity-50"
                style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
              >
                {savingKey ? "Saving..." : "Save"}
              </button>
            </div>
          ) : (
            <button
              onClick={() => handleSync("otter")}
              disabled={syncing !== null}
              className="text-sm px-3 py-1.5 uppercase disabled:opacity-50"
              style={{ background: "var(--bg-surface-warm)", color: "var(--color-text)" }}
            >
              {syncing === "otter" ? "Syncing..." : "Sync Now"}
            </button>
          )}
        </div>
      </div>

      {result && (
        <div className="grid grid-cols-3 gap-6 text-center">
          {[
            { label: "Files synced", value: result.files_synced },
            { label: "Entities", value: result.entities_extracted },
            { label: "Articles", value: result.articles_generated },
          ].map(stat => (
            <div key={stat.label} className="p-6" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)" }}>
              <div className="text-5xl" style={{ color: "var(--color-text)", letterSpacing: "-1.5px", lineHeight: 0.95 }}>{stat.value}</div>
              <div className="text-sm mt-2" style={{ color: "var(--color-text-muted)" }}>{stat.label}</div>
            </div>
          ))}
          {result.errors.length > 0 && (
            <div className="col-span-3 text-sm" style={{ color: "var(--color-error)" }}>
              {result.errors.map((e, i) => <div key={i}>{e}</div>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify build and commit**

```bash
cd openraven-ui && bun run build && git add src/pages/ConnectorsPage.tsx && git commit -m "feat(ui): redesign ConnectorsPage with warm cards and status badges"
```

---

### Task 12: Redesign GraphPage + GraphViewer + GraphNodeDetail

**Files:**
- Modify: `openraven-ui/src/pages/GraphPage.tsx`
- Modify: `openraven-ui/src/components/GraphViewer.tsx`
- Modify: `openraven-ui/src/components/GraphNodeDetail.tsx`

- [ ] **Step 1: Update GraphViewer with warm canvas and node colors**

In `openraven-ui/src/components/GraphViewer.tsx`, make these changes:

Replace the `TYPE_COLORS` constant (lines 37-44):
```tsx
const TYPE_COLORS: Record<string, string> = {
  technology: "#fa520f",
  concept: "#1f1f1f",
  person: "#ffa110",
  organization: "#d94800",
  event: "#b8860b",
  location: "#8b6914",
};
const DEFAULT_COLOR = "#999999";
```

Replace the canvas background color `#030712` everywhere it appears (lines 121-122 and 345-346) with `#fef9ef`:
```tsx
ctx.fillStyle = "#fef9ef";
```

Replace edge color `#374151` (lines 134, 155, 358, 379) with `rgba(31, 31, 31, 0.15)`:
```tsx
ctx.strokeStyle = isConnected ? "rgba(250, 82, 15, 0.4)" : "rgba(31, 31, 31, 0.15)";
```
and for arrowhead fill:
```tsx
ctx.fillStyle = isConnected ? "rgba(250, 82, 15, 0.4)" : "rgba(31, 31, 31, 0.15)";
```

Replace selected node stroke `#ffffff` (lines 179, 402) with `var(--color-brand)`:
```tsx
ctx.strokeStyle = "#fa520f";
```

Replace hover stroke `#60a5fa` (lines 186, 409) with brand:
```tsx
ctx.strokeStyle = "#fa520f";
```

Replace label color `#e5e7eb` (lines 195, 419) with `#1f1f1f`:
```tsx
ctx.fillStyle = dimmed ? "#1f1f1f55" : "#1f1f1f";
```

Replace dimmed label `#9ca3af55` with `#1f1f1f33`.

Replace the container className (line 428):
```tsx
<div ref={containerRef} className="flex-1 relative" style={{ background: "#fef9ef" }} data-testid="graph-viewer">
```

Replace empty state text class `text-gray-600` (line 431):
```tsx
<div className="absolute inset-0 flex items-center justify-center" style={{ color: "var(--color-text-muted)" }}>
```

- [ ] **Step 2: Update GraphNodeDetail with warm panel styling**

Replace the full content of `openraven-ui/src/components/GraphNodeDetail.tsx` with:

```tsx
interface GraphNodeDetailProps {
  node: {
    id: string;
    labels: string[];
    properties: Record<string, any>;
  } | null;
  neighbors: { id: string; labels: string[] }[];
  edges?: { target: string; description: string; keywords: string }[];
  onClose: () => void;
  onNavigate: (nodeId: string) => void;
}

const TYPE_COLORS: Record<string, string> = {
  technology: "#fa520f",
  concept: "#1f1f1f",
  person: "#ffa110",
  organization: "#d94800",
  event: "#b8860b",
  location: "#8b6914",
};

export default function GraphNodeDetail({ node, neighbors, edges, onClose, onNavigate }: GraphNodeDetailProps) {
  if (!node) return null;
  const edgeList = edges ?? [];

  const entityType = node.properties.entity_type ?? node.labels[0] ?? "unknown";
  const description = node.properties.description ?? "";
  const source = node.properties.file_path ?? node.properties.source_id ?? "";
  const typeColor = TYPE_COLORS[entityType] ?? "var(--color-text-muted)";

  return (
    <div className="w-80 p-4 overflow-y-auto" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)" }}>
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs uppercase tracking-wider px-2 py-0.5" style={{ background: "var(--bg-surface-warm)", color: typeColor }}>
          {entityType}
        </span>
        <button onClick={onClose} className="text-sm hover:opacity-70" style={{ color: "var(--color-text-muted)" }}>✕</button>
      </div>
      <h2 className="text-2xl mb-3" style={{ color: "var(--color-text)", lineHeight: 1.33 }}>{node.id}</h2>
      {description && (
        <p className="text-sm mb-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{description}</p>
      )}
      {source && (
        <div className="mb-4">
          <h3 className="text-xs uppercase tracking-wider mb-1" style={{ color: "var(--color-text-muted)" }}>Source</h3>
          <p className="text-sm break-all" style={{ color: "var(--color-text-secondary)" }}>{source}</p>
        </div>
      )}
      {neighbors.length > 0 && (
        <div>
          <h3 className="text-xs uppercase tracking-wider mb-2" style={{ color: "var(--color-text-muted)" }}>
            Connected ({neighbors.length})
          </h3>
          <div className="flex flex-col gap-2">
            {neighbors.map((n) => {
              const edge = edgeList.find(e => e.target === n.id);
              return (
                <div key={n.id} className="p-2" style={{ background: "var(--bg-surface-hover)", boxShadow: "var(--shadow-subtle)" }}>
                  <button
                    onClick={() => onNavigate(n.id)}
                    className="text-left text-sm truncate block hover:opacity-70"
                    style={{ color: "var(--color-brand)" }}
                  >
                    {n.id}
                  </button>
                  {edge?.description && (
                    <p className="text-xs mt-0.5 ml-2" style={{ color: "var(--color-text-muted)" }}>{edge.description}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Update GraphPage toolbar to warm design**

In `openraven-ui/src/pages/GraphPage.tsx`, replace the toolbar div (lines 148-200) with warm styling. Replace `bg-gray-950` → `background: var(--bg-surface)`, `border-gray-800` → `border-color: var(--color-border)`, update filter pills and inputs.

Replace the toolbar block (line 148 `<div className="flex items-center...` through line 200 `</div>`) with:

```tsx
      <div className="flex items-center gap-3 px-4 py-2" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-subtle)", borderBottom: "1px solid var(--color-border)" }}>
        <input
          type="text"
          placeholder="Search nodes..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="px-3 py-1 text-sm w-48 focus:outline-none focus:ring-2"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)", focusRingColor: "var(--color-brand)" }}
        />
        <div className="flex gap-1">
          {ENTITY_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => toggleType(type)}
              className="text-xs px-2 py-1"
              style={activeTypes.has(type)
                ? { background: "var(--color-brand)", color: "var(--color-text-on-brand)" }
                : { background: "var(--bg-surface-warm)", color: "var(--color-text-secondary)" }
              }
            >
              {type}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs" style={{ color: "var(--color-text-muted)" }}>Min connections:</label>
          <input
            type="range"
            min={0}
            max={10}
            value={minDegree}
            onChange={(e) => setMinDegree(Number(e.target.value))}
            className="w-20 h-1"
            style={{ accentColor: "var(--color-brand)" }}
          />
          <span className="text-xs w-4" style={{ color: "var(--color-text-secondary)" }}>{minDegree}</span>
        </div>
        <a
          href="/api/graph/export"
          download
          className="text-xs px-2 py-1 uppercase"
          style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
        >
          Export GraphML
        </a>
        <button
          onClick={exportPNG}
          className="text-xs px-2 py-1 uppercase"
          style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
        >
          Export PNG
        </button>
        <span className="text-xs ml-auto" style={{ color: "var(--color-text-muted)" }}>
          {filteredNodes.length} nodes / {filteredEdges.length} edges
          {data.is_truncated && " (truncated)"}
        </span>
      </div>
```

Also update the loading/error/empty state text colors in GraphPage:
- Line 134: Replace `text-gray-500 p-8` with `className="p-8" style={{ color: "var(--color-text-muted)" }}`
- Line 135: Replace `text-red-400 p-8` with `className="p-8" style={{ color: "var(--color-error)" }}`
- Lines 138-142: Replace `text-gray-500` with `style={{ color: "var(--color-text-muted)" }}` and `text-white` with `style={{ color: "var(--color-text)" }}`

- [ ] **Step 4: Verify build**

```bash
cd openraven-ui && bun run build
```

Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
cd openraven-ui && git add src/pages/GraphPage.tsx src/components/GraphViewer.tsx src/components/GraphNodeDetail.tsx
git commit -m "feat(ui): redesign Graph page with warm ivory canvas and golden shadow detail panel"
```

---

### Task 13: Final Visual Verification + Cleanup

**Files:**
- All modified files

- [ ] **Step 1: Run full build**

```bash
cd openraven-ui && bun run build
```

Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 2: Run existing tests**

```bash
cd openraven-ui && bun test tests/
```

Expected: All tests pass. If any fail due to class name assertions, update the test assertions to match new warm styling.

- [ ] **Step 3: Start dev server and visually verify**

```bash
cd openraven-ui && bun run dev
```

Open each page in browser and verify:
- [ ] Nav: block identity logo visible, warm white surface, golden shadow, orange active state
- [ ] Ask: warm ivory bg, gradient orange user bubbles, white assistant bubbles with golden shadow
- [ ] Ingest: warm upload zone with amber dashed border, dark "Browse Files" button
- [ ] Graph: ivory canvas, warm-colored nodes, orange hover highlight, warm toolbar
- [ ] Wiki: warm ivory sidebar, golden shadow content card
- [ ] Connectors: warm cards with golden shadow, cream status badges
- [ ] Status: golden shadow stat cards, cream LLM card

- [ ] **Step 4: Commit any test fixes**

```bash
cd openraven-ui && git add -A && git commit -m "fix(ui): update test assertions for Mistral Premium redesign"
```

(Only if test fixes were needed.)
