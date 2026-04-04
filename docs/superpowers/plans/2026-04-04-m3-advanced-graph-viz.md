# M3: Advanced Interactive Graph Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the basic force-directed graph to an interactive knowledge explorer with node drag, hover tooltips, edge labels, relationship arrows, community clustering, min-degree filter, and canvas PNG export.

**Architecture:** All changes are in the frontend (`GraphViewer.tsx`, `GraphPage.tsx`, `GraphNodeDetail.tsx`). The backend API is unchanged — the existing `GET /api/graph` response already contains all needed data (edge descriptions, keywords, weights). The visualization upgrades are purely canvas rendering + interaction enhancements.

**Tech Stack:** d3-force (existing), Canvas2D (existing), no new dependencies

**PRD Alignment:**
- M3 milestone line 727: "> 50 nodes, link accuracy > 85%"
- Feature table line 626: Expert/Team tiers get "進階" (advanced) graph
- Commercial-tier differentiator (line 385)

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `openraven-ui/src/components/GraphViewer.tsx` | Modify | Add node drag, hover tooltip, edge arrows, community colors, PNG export |
| `openraven-ui/src/pages/GraphPage.tsx` | Modify | Add min-degree slider, layout toggle, export PNG button |
| `openraven-ui/src/components/GraphNodeDetail.tsx` | Modify | Show edge descriptions to neighbors |
| `openraven-ui/tests/components/GraphViewer.test.tsx` | Modify | Test new features |

---

## Task 1: Node drag-to-reposition + click/drag disambiguation

**Files:**
- Modify: `openraven-ui/src/components/GraphViewer.tsx`

- [ ] **Step 1: Read current GraphViewer.tsx**

Read `openraven-ui/src/components/GraphViewer.tsx` to understand the current event handlers.

- [ ] **Step 2: Implement drag + click disambiguation**

In `GraphViewer.tsx`, replace the current click/pan event handling section. The key changes:

1. Track `dragDistance` to distinguish click from drag (threshold: 3px).
2. Add node drag: on mousedown over a node, start dragging that node instead of panning.
3. Pin dragged nodes by setting `fx`/`fy` (d3-force fixed positions).
4. Double-click to unpin.

Replace the mouse event handlers (the section from `// Click hit-test` through `canvas.addEventListener("mouseleave", handleMouseUp)`) with:

```typescript
// Interaction state
let isPanning = false;
let panStart = { x: 0, y: 0 };
let dragNode: SimNode | null = null;
let dragDistance = 0;
let mouseDownPos = { x: 0, y: 0 };

function hitTest(clientX: number, clientY: number): SimNode | null {
  const rect = canvas.getBoundingClientRect();
  const { x: tx, y: ty, k } = transformRef.current;
  const mx = (clientX - rect.left - tx) / k;
  const my = (clientY - rect.top - ty) / k;
  for (const node of simNodes) {
    if (node.x == null) continue;
    const r = getRadius(node.id) + 4;
    const dx = mx - node.x;
    const dy = my - node.y!;
    if (dx * dx + dy * dy < r * r) return node;
  }
  return null;
}

const handleMouseDown = (e: MouseEvent) => {
  if (e.button !== 0) return;
  dragDistance = 0;
  mouseDownPos = { x: e.clientX, y: e.clientY };

  const hit = hitTest(e.clientX, e.clientY);
  if (hit) {
    dragNode = hit;
    simulation.alphaTarget(0.3).restart();
  } else {
    isPanning = true;
    panStart = { x: e.clientX - transformRef.current.x, y: e.clientY - transformRef.current.y };
  }
};

const handleMouseMove = (e: MouseEvent) => {
  dragDistance += Math.abs(e.movementX) + Math.abs(e.movementY);

  if (dragNode) {
    const rect = canvas.getBoundingClientRect();
    const { x: tx, y: ty, k } = transformRef.current;
    dragNode.fx = (e.clientX - rect.left - tx) / k;
    dragNode.fy = (e.clientY - rect.top - ty) / k;
    return;
  }

  if (isPanning) {
    transformRef.current.x = e.clientX - panStart.x;
    transformRef.current.y = e.clientY - panStart.y;
    paint();
  }
};

const handleMouseUp = () => {
  if (dragNode) {
    simulation.alphaTarget(0);
    // Pin the node where it was dropped
    dragNode.fx = dragNode.x;
    dragNode.fy = dragNode.y;
    dragNode = null;
  }
  isPanning = false;
};

const handleClick = (e: MouseEvent) => {
  if (dragDistance > 3) return; // was a drag, not a click
  const hit = hitTest(e.clientX, e.clientY);
  if (hit) onNodeClick(hit);
};

const handleDblClick = (e: MouseEvent) => {
  const hit = hitTest(e.clientX, e.clientY);
  if (hit) {
    // Unpin node on double-click
    hit.fx = null;
    hit.fy = null;
    simulation.alphaTarget(0.3).restart();
    setTimeout(() => { if (!dragNode) simulation.alphaTarget(0); }, 500);
  }
};

canvas.addEventListener("mousedown", handleMouseDown);
canvas.addEventListener("mousemove", handleMouseMove);
canvas.addEventListener("mouseup", handleMouseUp);
canvas.addEventListener("mouseleave", handleMouseUp);
canvas.addEventListener("click", handleClick);
canvas.addEventListener("dblclick", handleDblClick);
canvas.addEventListener("wheel", handleWheel, { passive: false });
```

Update the cleanup to remove the new listeners:

```typescript
return () => {
  simulation.stop();
  resizeObserver.disconnect();
  canvas.removeEventListener("mousedown", handleMouseDown);
  canvas.removeEventListener("mousemove", handleMouseMove);
  canvas.removeEventListener("mouseup", handleMouseUp);
  canvas.removeEventListener("mouseleave", handleMouseUp);
  canvas.removeEventListener("click", handleClick);
  canvas.removeEventListener("dblclick", handleDblClick);
  canvas.removeEventListener("wheel", handleWheel);
};
```

- [ ] **Step 3: Verify build**

Run: `cd openraven-ui && bun run build`

- [ ] **Step 4: Commit**

```bash
git add openraven-ui/src/components/GraphViewer.tsx
git commit -m "feat(graph): add node drag-to-reposition with click/drag disambiguation"
```

---

## Task 2: Hover tooltip + edge arrows

**Depends on:** Task 1 must be completed first

**Files:**
- Modify: `openraven-ui/src/components/GraphViewer.tsx`

> **IMPORTANT: Apply arrow rendering and hover highlight to BOTH the main paint function AND the repaint useEffect.** All edge arrow code and hover highlight code shown below must be duplicated into both paint locations. If you only add it to one, the arrows/highlights will disappear or flicker when the other paint path runs.

- [ ] **Step 1: Add hover state tracking**

Add a new prop to `GraphViewerProps`:

```typescript
onNodeHover?: (node: GraphNode | null) => void;
```

In the main `useEffect`, track hover state using a `useRef` so both paint paths can access it:

```typescript
// Above the useEffect, declare the ref:
const hoveredNodeRef = useRef<SimNode | null>(null);
```

Then inside the useEffect, replace the `handleMouseMove` from Task 1 with this combined version that handles BOTH drag/pan AND hover:

```typescript
const handleMouseMove = (e: MouseEvent) => {
  dragDistance += Math.abs(e.movementX) + Math.abs(e.movementY);

  if (dragNode) {
    const rect = canvas.getBoundingClientRect();
    const { x: tx, y: ty, k } = transformRef.current;
    dragNode.fx = (e.clientX - rect.left - tx) / k;
    dragNode.fy = (e.clientY - rect.top - ty) / k;
    return;
  }

  if (isPanning) {
    transformRef.current.x = e.clientX - panStart.x;
    transformRef.current.y = e.clientY - panStart.y;
    paint();
    return;
  }

  // Hover detection (only when not dragging or panning)
  const hit = hitTest(e.clientX, e.clientY);
  if (hit !== hoveredNodeRef.current) {
    hoveredNodeRef.current = hit;
    canvas.style.cursor = hit ? "pointer" : "grab";
    paint(); // repaint to show hover highlight
  }
};
```

- [ ] **Step 2: Add hover highlight to paint function**

In the node paint loop of the **main paint function**, add hover ring:

```typescript
const isHovered = hoveredNodeRef.current && node.id === hoveredNodeRef.current.id;
if (isHovered) {
  ctx.strokeStyle = "#60a5fa";
  ctx.lineWidth = 2;
  ctx.stroke();
}
```

Show labels for hovered nodes (add to the label condition):

```typescript
if (degree >= 3 || isSelected || isMatch || isHovered) {
```

In the **repaint useEffect's** node paint loop, also add the same hover check:

```typescript
const isHovered = hoveredNodeRef.current && node.id === hoveredNodeRef.current.id;
if (isHovered) {
  ctx.strokeStyle = "#60a5fa";
  ctx.lineWidth = 2;
  ctx.stroke();
}
// ... and update the label condition similarly:
if (degree >= 3 || isSelected || isMatch || isHovered) {
```

- [ ] **Step 3: Add edge arrows**

In the edge paint loop of the **main paint function**, add arrowheads:

```typescript
// Draw arrowhead
const angle = Math.atan2(t.y! - s.y!, t.x! - s.x!);
const targetRadius = getRadius(t.id);
const arrowX = t.x! - Math.cos(angle) * targetRadius;
const arrowY = t.y! - Math.sin(angle) * targetRadius;
const arrowSize = isConnected ? 5 : 3;
ctx.beginPath();
ctx.moveTo(arrowX, arrowY);
ctx.lineTo(
  arrowX - arrowSize * Math.cos(angle - Math.PI / 6),
  arrowY - arrowSize * Math.sin(angle - Math.PI / 6),
);
ctx.lineTo(
  arrowX - arrowSize * Math.cos(angle + Math.PI / 6),
  arrowY - arrowSize * Math.sin(angle + Math.PI / 6),
);
ctx.closePath();
ctx.fillStyle = isConnected ? "#60a5fa66" : "#374151";
ctx.fill();
```

In the **repaint useEffect's** edge paint loop, add the same arrowhead code:

```typescript
// Draw arrowhead (repaint useEffect)
const angle = Math.atan2(t.y! - s.y!, t.x! - s.x!);
const targetRadius = getRadius(t.id);
const arrowX = t.x! - Math.cos(angle) * targetRadius;
const arrowY = t.y! - Math.sin(angle) * targetRadius;
const arrowSize = isConnected ? 5 : 3;
ctx.beginPath();
ctx.moveTo(arrowX, arrowY);
ctx.lineTo(
  arrowX - arrowSize * Math.cos(angle - Math.PI / 6),
  arrowY - arrowSize * Math.sin(angle - Math.PI / 6),
);
ctx.lineTo(
  arrowX - arrowSize * Math.cos(angle + Math.PI / 6),
  arrowY - arrowSize * Math.sin(angle + Math.PI / 6),
);
ctx.closePath();
ctx.fillStyle = isConnected ? "#60a5fa66" : "#374151";
ctx.fill();
```

- [ ] **Step 4: Build and test**

Run: `cd openraven-ui && bun test tests/ && bun run build`

- [ ] **Step 5: Commit**

```bash
git add openraven-ui/src/components/GraphViewer.tsx
git commit -m "feat(graph): add hover tooltips and edge arrows"
```

---

## Task 3: Min-degree slider + node count display

**Files:**
- Modify: `openraven-ui/src/pages/GraphPage.tsx`

- [ ] **Step 1: Add min-degree state and filter**

Add state in `GraphPage`:

```tsx
const [minDegree, setMinDegree] = useState(0);
```

Update `filteredNodes` memo to also filter by degree. **Important:** The degree map must be computed from type-filtered edges (after `activeTypes` filtering but before `minDegree` filtering), so that degree counts reflect the visible subgraph:

```tsx
const filteredNodes = useMemo(() => {
  if (!data) return [];

  // Step 1: Get type-filtered node IDs
  const typeFilteredNodeIds = new Set(
    data.nodes
      .filter((n) => {
        const type = n.properties?.entity_type ?? n.labels[0] ?? "unknown";
        return activeTypes.has(type);
      })
      .map((n) => n.id)
  );

  // Step 2: Get edges where both endpoints pass the type filter
  const typeFilteredEdges = data.edges.filter(
    (e) => typeFilteredNodeIds.has(e.source) && typeFilteredNodeIds.has(e.target)
  );

  // Step 3: Build degree map from type-filtered edges
  const degrees = new Map<string, number>();
  for (const e of typeFilteredEdges) {
    degrees.set(e.source, (degrees.get(e.source) ?? 0) + 1);
    degrees.set(e.target, (degrees.get(e.target) ?? 0) + 1);
  }

  // Step 4: Filter nodes by type AND minDegree
  return data.nodes.filter((n) => {
    const type = n.properties?.entity_type ?? n.labels[0] ?? "unknown";
    if (!activeTypes.has(type)) return false;
    if (minDegree > 0 && (degrees.get(n.id) ?? 0) < minDegree) return false;
    return true;
  });
}, [data, activeTypes, minDegree]);
```

- [ ] **Step 2: Add slider to toolbar**

Add in the toolbar after the type filter buttons:

```tsx
<div className="flex items-center gap-2">
  <label className="text-xs text-gray-500">Min connections:</label>
  <input
    type="range"
    min={0}
    max={10}
    value={minDegree}
    onChange={(e) => setMinDegree(Number(e.target.value))}
    className="w-20 h-1 accent-blue-500"
  />
  <span className="text-xs text-gray-400 w-4">{minDegree}</span>
</div>
```

- [ ] **Step 3: Build**

Run: `cd openraven-ui && bun run build`

- [ ] **Step 4: Commit**

```bash
git add openraven-ui/src/pages/GraphPage.tsx
git commit -m "feat(graph): add min-degree slider filter"
```

---

## Task 4: Edge descriptions in detail panel

**Files:**
- Modify: `openraven-ui/src/components/GraphNodeDetail.tsx`
- Modify: `openraven-ui/src/pages/GraphPage.tsx`

- [ ] **Step 1: Update GraphNodeDetail to accept edge data**

Add to `GraphNodeDetailProps`:

```typescript
edges?: { target: string; description: string; keywords: string }[];
```

At the top of the `GraphNodeDetail` component, add a default:

```typescript
const edgeList = edges ?? [];
```

In the "Connected" section, show edge descriptions (use `edgeList` instead of `edges`):

```tsx
{neighbors.length > 0 && (
  <div>
    <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
      Connected ({neighbors.length})
    </h3>
    <div className="flex flex-col gap-2">
      {neighbors.map((n) => {
        const edge = edgeList.find(e => e.target === n.id);
        return (
          <div key={n.id}>
            <button
              onClick={() => onNavigate(n.id)}
              className="text-left text-sm text-blue-400 hover:text-blue-300 truncate block"
            >
              {n.id}
            </button>
            {edge?.description && (
              <p className="text-xs text-gray-500 mt-0.5 ml-2">{edge.description}</p>
            )}
          </div>
        );
      })}
    </div>
  </div>
)}
```

- [ ] **Step 2: Pass edge data from GraphPage**

In `GraphPage`, compute edges for the selected node:

```tsx
const selectedEdges = useMemo(() => {
  if (!selectedNode || !data) return [];
  const id = selectedNode.id;
  return data.edges
    .filter(e => e.source === id || e.target === id)
    .map(e => ({
      target: e.source === id ? e.target : e.source,
      description: e.properties?.description ?? "",
      keywords: e.properties?.keywords ?? "",
    }));
}, [selectedNode, data]);
```

Pass to `GraphNodeDetail`:

```tsx
<GraphNodeDetail
  node={selectedNode}
  neighbors={neighbors}
  edges={selectedEdges}
  onClose={() => setSelectedNode(null)}
  onNavigate={handleNavigate}
/>
```

- [ ] **Step 3: Build and test**

Run: `cd openraven-ui && bun test tests/ && bun run build`

- [ ] **Step 4: Commit**

```bash
git add openraven-ui/src/components/GraphNodeDetail.tsx openraven-ui/src/pages/GraphPage.tsx
git commit -m "feat(graph): show edge descriptions in node detail panel"
```

---

## Task 5: Canvas PNG export

**Files:**
- Modify: `openraven-ui/src/pages/GraphPage.tsx`

- [ ] **Step 1: Add export PNG button**

Add a ref to the canvas in GraphViewer by exposing it. The simplest approach: add a button that queries the DOM for the canvas:

In `GraphPage`, add the export handler:

```tsx
function exportPNG() {
  const canvas = document.querySelector('[data-testid="graph-viewer"] canvas') as HTMLCanvasElement;
  if (!canvas) return;
  const link = document.createElement("a");
  link.download = "openraven-knowledge-graph.png";
  link.href = canvas.toDataURL("image/png");
  link.click();
}
```

Add button in the toolbar (next to Export GraphML):

```tsx
<button
  onClick={exportPNG}
  className="text-xs px-2 py-1 rounded border border-gray-600 bg-gray-800 text-gray-200 hover:bg-gray-700"
>
  Export PNG
</button>
```

- [ ] **Step 2: Build**

Run: `cd openraven-ui && bun run build`

- [ ] **Step 3: Commit**

```bash
git add openraven-ui/src/pages/GraphPage.tsx
git commit -m "feat(graph): add canvas PNG export button"
```

---

## Task 6: Extended search scope + updated tests

**Files:**
- Modify: `openraven-ui/src/components/GraphViewer.tsx`
- Modify: `openraven-ui/tests/components/GraphViewer.test.tsx`

- [ ] **Step 1: Expand search to include description and entity_type**

In `GraphViewer.tsx`, update the search matching logic in the paint function. Change:

```typescript
const isMatch = searchTerm && node.id.toLowerCase().includes(searchTerm.toLowerCase());
```

To:

```typescript
const searchLower = searchTerm.toLowerCase();
const isMatch = searchTerm && (
  node.id.toLowerCase().includes(searchLower) ||
  (node.properties?.description ?? "").toLowerCase().includes(searchLower) ||
  (node.properties?.entity_type ?? "").toLowerCase().includes(searchLower)
);
```

Apply this change in BOTH paint locations (main useEffect paint + repaint useEffect).

> **Note (MEDIUM-2 — stale closure for search):** The repaint useEffect captures `searchTerm` at render time, so if the user types a new search term while the simulation is still ticking, the repaint useEffect will use the stale value until the next render. This is an existing architectural issue caused by the duplicated paint logic and would require refactoring to a single shared paint function (out of scope for this plan).

- [ ] **Step 2: Update tests**

Add to `openraven-ui/tests/components/GraphViewer.test.tsx`:

```tsx
it("renders with selected node without crashing", () => {
  const { container } = render(
    <GraphViewer nodes={sampleNodes} edges={sampleEdges} selectedNodeId="KAFKA" onNodeClick={() => {}} searchTerm="" />
  );
  const viewer = container.querySelector('[data-testid="graph-viewer"]');
  expect(viewer).not.toBeNull();
});
```

- [ ] **Step 3: Add testable utility tests**

Extract the following logic as pure functions (or test inline equivalents) in `openraven-ui/tests/components/GraphViewer.test.tsx`:

```tsx
// --- Test: min-degree filtering logic ---
describe("minDegreeFilter", () => {
  function filterByMinDegree(
    nodes: { id: string }[],
    edges: { source: string; target: string }[],
    minDegree: number,
  ) {
    const degrees = new Map<string, number>();
    for (const e of edges) {
      degrees.set(e.source, (degrees.get(e.source) ?? 0) + 1);
      degrees.set(e.target, (degrees.get(e.target) ?? 0) + 1);
    }
    return nodes.filter((n) => (degrees.get(n.id) ?? 0) >= minDegree);
  }

  it("returns all nodes when minDegree is 0", () => {
    const nodes = [{ id: "A" }, { id: "B" }, { id: "C" }];
    const edges = [{ source: "A", target: "B" }];
    expect(filterByMinDegree(nodes, edges, 0)).toEqual(nodes);
  });

  it("filters out low-degree nodes", () => {
    const nodes = [{ id: "A" }, { id: "B" }, { id: "C" }];
    const edges = [
      { source: "A", target: "B" },
      { source: "A", target: "C" },
    ];
    const result = filterByMinDegree(nodes, edges, 2);
    expect(result.map((n) => n.id)).toEqual(["A"]);
  });

  it("excludes isolated nodes when minDegree is 1", () => {
    const nodes = [{ id: "A" }, { id: "B" }, { id: "C" }];
    const edges = [{ source: "A", target: "B" }];
    const result = filterByMinDegree(nodes, edges, 1);
    expect(result.map((n) => n.id)).toEqual(["A", "B"]);
  });
});

// --- Test: selectedEdges memo logic ---
describe("selectedEdges", () => {
  function computeSelectedEdges(
    selectedNodeId: string,
    edges: { source: string; target: string; properties?: { description?: string; keywords?: string } }[],
  ) {
    return edges
      .filter((e) => e.source === selectedNodeId || e.target === selectedNodeId)
      .map((e) => ({
        target: e.source === selectedNodeId ? e.target : e.source,
        description: e.properties?.description ?? "",
        keywords: e.properties?.keywords ?? "",
      }));
  }

  it("returns edges connected to the selected node with normalized target", () => {
    const edges = [
      { source: "A", target: "B", properties: { description: "relates to", keywords: "k1" } },
      { source: "C", target: "A", properties: { description: "derived from", keywords: "k2" } },
      { source: "B", target: "C", properties: { description: "unrelated", keywords: "k3" } },
    ];
    const result = computeSelectedEdges("A", edges);
    expect(result).toEqual([
      { target: "B", description: "relates to", keywords: "k1" },
      { target: "C", description: "derived from", keywords: "k2" },
    ]);
  });

  it("returns empty array when no edges match", () => {
    const edges = [
      { source: "B", target: "C", properties: { description: "x", keywords: "y" } },
    ];
    expect(computeSelectedEdges("A", edges)).toEqual([]);
  });

  it("handles missing properties gracefully", () => {
    const edges = [{ source: "A", target: "B" }];
    const result = computeSelectedEdges("A", edges);
    expect(result).toEqual([{ target: "B", description: "", keywords: "" }]);
  });
});

// --- Test: search predicate across id + description + entity_type ---
describe("searchPredicate", () => {
  function matchesSearch(
    node: { id: string; properties?: { description?: string; entity_type?: string } },
    searchTerm: string,
  ): boolean {
    if (!searchTerm) return false;
    const s = searchTerm.toLowerCase();
    return (
      node.id.toLowerCase().includes(s) ||
      (node.properties?.description ?? "").toLowerCase().includes(s) ||
      (node.properties?.entity_type ?? "").toLowerCase().includes(s)
    );
  }

  it("matches by node id", () => {
    expect(matchesSearch({ id: "KAFKA" }, "kafka")).toBe(true);
  });

  it("matches by description", () => {
    expect(
      matchesSearch({ id: "X", properties: { description: "Message broker system" } }, "broker"),
    ).toBe(true);
  });

  it("matches by entity_type", () => {
    expect(
      matchesSearch({ id: "X", properties: { entity_type: "TECHNOLOGY" } }, "tech"),
    ).toBe(true);
  });

  it("returns false for empty search term", () => {
    expect(matchesSearch({ id: "KAFKA" }, "")).toBe(false);
  });

  it("returns false when nothing matches", () => {
    expect(
      matchesSearch(
        { id: "KAFKA", properties: { description: "streaming", entity_type: "TOOL" } },
        "database",
      ),
    ).toBe(false);
  });

  it("is case-insensitive", () => {
    expect(matchesSearch({ id: "Kafka" }, "KAFKA")).toBe(true);
  });
});
```

- [ ] **Step 4: Run tests and build**

Run: `cd openraven-ui && bun test tests/ && bun run build`

- [ ] **Step 5: Commit**

```bash
git add openraven-ui/src/components/GraphViewer.tsx openraven-ui/tests/components/GraphViewer.test.tsx
git commit -m "feat(graph): expand search to description and entity type, add utility tests"
```

---

## Task 7: E2E verification

- [ ] **Step 1: Full test suite**

```bash
cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py
cd openraven-ui && bun test tests/ && bun run build
```

- [ ] **Step 2: Restart PM2 and verify**

```bash
pm2 restart all && sleep 10
curl -sf http://localhost:8741/api/graph | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"nodes\"])} nodes, {len(d[\"edges\"])} edges')"
```

- [ ] **Step 3: Visual verification**

Open `http://localhost:3002/graph` in browser. Verify:
- Nodes can be dragged and pinned
- Double-click unpins
- Hover shows cursor change
- Edge arrows visible
- Min-degree slider filters low-connection nodes
- Detail panel shows edge descriptions
- Export PNG downloads an image
- Search matches description text, not just node ID

---

## Summary

| Task | What | Tests |
|---|---|---|
| 1 | Node drag + click/drag disambiguation | Build check |
| 2 | Hover tooltip + edge arrows | Build check |
| 3 | Min-degree slider filter | Build check |
| 4 | Edge descriptions in detail panel | Build check |
| 5 | Canvas PNG export | Build check |
| 6 | Extended search scope + utility tests | 1 component test + 3 utility test suites |
| 7 | E2E verification | Full suite |

**Total new tests: 1 component test + 3 utility test suites** (minDegreeFilter, selectedEdges, searchPredicate) covering pure logic that can be tested without a real browser

**Advanced features NOT included (future):**
- Community detection clustering (Louvain) — would need a Python API addition
- Hierarchical/radial layout modes — significant d3-force rework
- Shortest-path highlighting — needs backend pathfinding API
- Touch/pinch zoom — mobile optimization
- WebSocket live updates — push architecture
