# Knowledge Graph UX Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add embedded MiniGraph in Ask page, upgrade Graph page with dynamic filters/highlight/improved detail panel, and create two new backend APIs for subgraph and node context retrieval.

**Architecture:** Two new Python API endpoints (`/api/graph/subgraph` and `/api/graph/node/{id}/context`) backed by networkx GraphML reads and .md file scanning. Frontend adds a `MiniGraph` component using a `mode` prop on `GraphViewer`, upgrades `GraphNodeDetail` with async context loading, and makes `GraphPage` filters dynamic with URL highlight support.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript (frontend), d3-force (unchanged), networkx (GraphML), react-i18next (12 locales)

---

## File Structure

### Backend (Python)

| File | Action | Responsibility |
|------|--------|---------------|
| `openraven/src/openraven/graph/rag.py` | Modify | Add `get_subgraph()` and `get_node_context()` methods |
| `openraven/src/openraven/api/server.py` | Modify | Add 2 new API routes |
| `openraven/tests/test_graph.py` | Modify | Add tests for new graph methods |
| `openraven/tests/test_api.py` | Modify | Add API-level tests for new endpoints |

### Frontend (React/TypeScript)

| File | Action | Responsibility |
|------|--------|---------------|
| `openraven-ui/src/components/GraphViewer.tsx` | Modify | Add `mode` and `focusNodeId` props |
| `openraven-ui/src/components/MiniGraph.tsx` | Create | Subgraph fetch + mini GraphViewer + floating card |
| `openraven-ui/src/components/GraphNodeDetail.tsx` | Modify | Async context, multi-source, action buttons |
| `openraven-ui/src/pages/GraphPage.tsx` | Modify | Dynamic filters, guide bar, URL highlight |
| `openraven-ui/src/pages/AskPage.tsx` | Modify | Embed MiniGraph below sources |
| `openraven-ui/public/locales/*/graph.json` | Modify | New i18n keys (12 locales) |

---

### Task 1: Backend — `get_subgraph()` method

**Files:**
- Modify: `openraven/src/openraven/graph/rag.py`
- Modify: `openraven/tests/test_graph.py`

- [ ] **Step 1: Write failing test for get_subgraph with entities**

Add to `openraven/tests/test_graph.py`:

```python
def _create_test_graphml(working_dir: Path) -> None:
    """Create a small test GraphML file for subgraph/context tests."""
    import networkx as nx

    graph = nx.DiGraph()
    graph.add_node("個資法第27條", entity_type="statute", description="Article 27 of PDPA",
                   file_path="/data/pdpa.md", source_id="chunk-1")
    graph.add_node("個人資料盤點", entity_type="concept", description="Personal data inventory",
                   file_path="/data/pdpa.md", source_id="chunk-1")
    graph.add_node("安全維護計畫", entity_type="concept", description="Security maintenance plan",
                   file_path="/data/compliance.md", source_id="chunk-2")
    graph.add_node("個資法第48條", entity_type="statute", description="Article 48 penalties",
                   file_path="/data/compliance.md", source_id="chunk-3")
    graph.add_node("獨立節點", entity_type="concept", description="Isolated node",
                   file_path="/data/other.md", source_id="chunk-4")

    graph.add_edge("個資法第27條", "個人資料盤點", description="requires", keywords="requirement")
    graph.add_edge("個資法第27條", "安全維護計畫", description="requires", keywords="requirement")
    graph.add_edge("安全維護計畫", "個資法第48條", description="penalty for violation", keywords="penalty")

    nx.write_graphml(graph, str(working_dir / "graph_chunk_entity_relation.graphml"))


def test_get_subgraph_by_entities(graph: RavenGraph) -> None:
    _create_test_graphml(graph.working_dir)
    result = graph.get_subgraph(entities=["個資法第27條"], max_nodes=30)
    node_ids = {n["id"] for n in result["nodes"]}
    assert "個資法第27條" in node_ids
    assert "個人資料盤點" in node_ids
    assert "安全維護計畫" in node_ids
    assert "獨立節點" not in node_ids
    seed_nodes = [n for n in result["nodes"] if n.get("is_seed")]
    assert len(seed_nodes) == 1
    assert seed_nodes[0]["id"] == "個資法第27條"
    assert len(result["edges"]) >= 2


def test_get_subgraph_by_files(graph: RavenGraph) -> None:
    _create_test_graphml(graph.working_dir)
    result = graph.get_subgraph(files=["pdpa.md"], max_nodes=30)
    node_ids = {n["id"] for n in result["nodes"]}
    assert "個資法第27條" in node_ids
    assert "個人資料盤點" in node_ids


def test_get_subgraph_empty(graph: RavenGraph) -> None:
    result = graph.get_subgraph(entities=["nonexistent"], max_nodes=30)
    assert result["nodes"] == []
    assert result["edges"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd openraven && source .venv/bin/activate && pytest tests/test_graph.py::test_get_subgraph_by_entities tests/test_graph.py::test_get_subgraph_by_files tests/test_graph.py::test_get_subgraph_empty -v`
Expected: FAIL with `AttributeError: 'RavenGraph' object has no attribute 'get_subgraph'`

- [ ] **Step 3: Implement get_subgraph in rag.py**

Add this method to the `RavenGraph` class in `openraven/src/openraven/graph/rag.py`, after the `get_graph_data` method:

```python
def get_subgraph(
    self,
    entities: list[str] | None = None,
    files: list[str] | None = None,
    max_nodes: int = 30,
) -> dict:
    """Return a subgraph centered on the given entities or files, with 1-hop neighbors."""
    import networkx as nx

    graph_file = self.working_dir / "graph_chunk_entity_relation.graphml"
    if not graph_file.exists():
        return {"nodes": [], "edges": []}

    try:
        graph = nx.read_graphml(str(graph_file))
    except Exception:
        return {"nodes": [], "edges": []}

    seed_ids: set[str] = set()

    if entities:
        for eid in entities:
            if eid in graph:
                seed_ids.add(eid)

    if files:
        file_suffixes = {f.split("/")[-1] for f in files}
        for node_id, attrs in graph.nodes(data=True):
            file_path = attrs.get("file_path", "")
            for part in file_path.split("<SEP>"):
                fname = part.strip().split("/")[-1]
                if fname in file_suffixes:
                    seed_ids.add(node_id)
                    break

    if not seed_ids:
        return {"nodes": [], "edges": []}

    # BFS 1-hop neighbors
    neighbor_ids: set[str] = set()
    for sid in seed_ids:
        if graph.has_node(sid):
            neighbor_ids.update(graph.predecessors(sid))
            neighbor_ids.update(graph.successors(sid))
    all_ids = seed_ids | neighbor_ids

    # Trim if exceeding max_nodes — keep seeds, sort neighbors by degree
    if len(all_ids) > max_nodes:
        extras = all_ids - seed_ids
        ranked = sorted(extras, key=lambda n: graph.degree(n), reverse=True)
        all_ids = seed_ids | set(ranked[: max_nodes - len(seed_ids)])

    nodes = []
    for node_id in all_ids:
        attrs = dict(graph.nodes[node_id])
        nodes.append({
            "id": node_id,
            "labels": [attrs.get("entity_type", "unknown")],
            "properties": attrs,
            "is_seed": node_id in seed_ids,
        })

    edges = []
    for source, target, attrs in graph.edges(data=True):
        if source in all_ids and target in all_ids:
            edges.append({
                "id": f"{source}-{target}",
                "type": "DIRECTED",
                "source": source,
                "target": target,
                "properties": dict(attrs),
            })

    return {"nodes": nodes, "edges": edges}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd openraven && source .venv/bin/activate && pytest tests/test_graph.py::test_get_subgraph_by_entities tests/test_graph.py::test_get_subgraph_by_files tests/test_graph.py::test_get_subgraph_empty -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven/src/openraven/graph/rag.py openraven/tests/test_graph.py
git commit -m "feat(graph): add get_subgraph method for entity/file-based subgraph extraction"
```

---

### Task 2: Backend — `get_node_context()` method

**Files:**
- Modify: `openraven/src/openraven/graph/rag.py`
- Modify: `openraven/tests/test_graph.py`

- [ ] **Step 1: Write failing test**

Add to `openraven/tests/test_graph.py`:

```python
def test_get_node_context(graph: RavenGraph, tmp_working_dir: Path) -> None:
    _create_test_graphml(graph.working_dir)
    # Create a fake source .md file in the working_dir parent (simulating ingested docs)
    md_file = tmp_working_dir / "pdpa.md"
    md_file.write_text(
        "# 個資法\n\n## 第 27 條\n\n依個資法第 27 條及施行細則第 12 條，企業應建立個資安全維護計畫。\n\n## 第 48 條\n\n違反者處罰鍰。\n",
        encoding="utf-8",
    )
    result = graph.get_node_context("個資法第27條", search_dirs=[tmp_working_dir])
    assert result["node_id"] == "個資法第27條"
    assert len(result["excerpts"]) >= 1
    assert "個資法第 27 條" in result["excerpts"][0]["text"]
    assert "pdpa.md" in result["excerpts"][0]["file"]
    assert len(result["files"]) >= 1


def test_get_node_context_not_found(graph: RavenGraph, tmp_working_dir: Path) -> None:
    result = graph.get_node_context("不存在的節點", search_dirs=[tmp_working_dir])
    assert result["node_id"] == "不存在的節點"
    assert result["excerpts"] == []
    assert result["files"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd openraven && source .venv/bin/activate && pytest tests/test_graph.py::test_get_node_context tests/test_graph.py::test_get_node_context_not_found -v`
Expected: FAIL with `AttributeError: 'RavenGraph' object has no attribute 'get_node_context'`

- [ ] **Step 3: Implement get_node_context in rag.py**

Add this method to `RavenGraph` in `openraven/src/openraven/graph/rag.py`, after `get_subgraph`:

```python
def get_node_context(
    self,
    node_id: str,
    search_dirs: list[Path] | None = None,
    max_excerpt_chars: int = 500,
    context_lines: int = 3,
) -> dict:
    """Search .md files for passages mentioning node_id, return excerpts."""
    if search_dirs is None:
        search_dirs = [self.working_dir.parent]

    excerpts: list[dict] = []
    seen_files: set[str] = set()

    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        for md_file in sorted(search_dir.rglob("*.md")):
            fname = md_file.name
            if fname.startswith("."):
                continue
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                continue
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if node_id in line and fname not in seen_files:
                    seen_files.add(fname)
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    text = "\n".join(lines[start:end])
                    if len(text) > max_excerpt_chars:
                        text = text[:max_excerpt_chars] + "..."
                    excerpts.append({
                        "file": fname,
                        "text": text,
                        "line_start": start + 1,
                        "line_end": end,
                    })
                    break

    return {
        "node_id": node_id,
        "excerpts": excerpts,
        "files": list(seen_files),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd openraven && source .venv/bin/activate && pytest tests/test_graph.py::test_get_node_context tests/test_graph.py::test_get_node_context_not_found -v`
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven/src/openraven/graph/rag.py openraven/tests/test_graph.py
git commit -m "feat(graph): add get_node_context method for original text retrieval"
```

---

### Task 3: Backend — API endpoints

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Add to `openraven/tests/test_api.py`:

```python
def test_graph_subgraph_entities(client):
    """GET /api/graph/subgraph with entities param returns subgraph."""
    res = client.get("/api/graph/subgraph", params={"entities": "nonexistent"})
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data


def test_graph_subgraph_files(client):
    """GET /api/graph/subgraph with files param returns subgraph."""
    res = client.get("/api/graph/subgraph", params={"files": "test.md"})
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data


def test_graph_node_context(client):
    """GET /api/graph/node/{id}/context returns context."""
    res = client.get("/api/graph/node/testnode/context")
    assert res.status_code == 200
    data = res.json()
    assert data["node_id"] == "testnode"
    assert "excerpts" in data
    assert "files" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd openraven && source .venv/bin/activate && pytest tests/test_api.py::test_graph_subgraph_entities tests/test_api.py::test_graph_subgraph_files tests/test_api.py::test_graph_node_context -v`
Expected: FAIL with 404 or similar

- [ ] **Step 3: Add API routes to server.py**

Add these routes in `openraven/src/openraven/api/server.py`, after the existing `@app.get("/api/graph")` route (around line 400):

```python
@app.get("/api/graph/subgraph")
async def graph_subgraph(
    request: Request,
    entities: str | None = Query(default=None),
    files: str | None = Query(default=None),
    max_nodes: int = Query(default=30, ge=1, le=200),
):
    pipe = resolve_pipeline(request)
    entity_list = [e.strip() for e in entities.split(",") if e.strip()] if entities else None
    file_list = [f.strip() for f in files.split(",") if f.strip()] if files else None
    data = await asyncio.get_event_loop().run_in_executor(
        None, lambda: pipe.graph.get_subgraph(entities=entity_list, files=file_list, max_nodes=max_nodes)
    )
    return data

@app.get("/api/graph/node/{node_id}/context")
async def graph_node_context(request: Request, node_id: str):
    pipe = resolve_pipeline(request)
    search_dirs = [pipe.config.working_dir]
    data = await asyncio.get_event_loop().run_in_executor(
        None, lambda: pipe.graph.get_node_context(node_id, search_dirs=search_dirs)
    )
    return data
```

Note: The `/api/graph/subgraph` route must be defined BEFORE `/api/graph/node/{node_id}/context` and AFTER `/api/graph/export` to avoid route conflicts. Place both after the existing `/api/graph` route.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd openraven && source .venv/bin/activate && pytest tests/test_api.py::test_graph_subgraph_entities tests/test_api.py::test_graph_subgraph_files tests/test_api.py::test_graph_node_context -v`
Expected: 3 PASSED

- [ ] **Step 5: Run all existing graph tests to verify no regressions**

Run: `cd openraven && source .venv/bin/activate && pytest tests/test_graph.py tests/test_api.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven/src/openraven/api/server.py openraven/tests/test_api.py
git commit -m "feat(api): add /api/graph/subgraph and /api/graph/node/:id/context endpoints"
```

---

### Task 4: Frontend — GraphViewer mode + focusNodeId props

**Files:**
- Modify: `openraven-ui/src/components/GraphViewer.tsx`

- [ ] **Step 1: Add mode and focusNodeId to GraphViewerProps interface**

In `openraven-ui/src/components/GraphViewer.tsx`, replace the `GraphViewerProps` interface and `TYPE_COLORS`:

```typescript
interface GraphViewerProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: string | null;
  onNodeClick: (node: GraphNode) => void;
  searchTerm: string;
  mode?: "full" | "mini";
  focusNodeId?: string | null;
}

const TYPE_COLORS: Record<string, string> = {
  technology: "#fa520f",
  concept: "#1f1f1f",
  person: "#ffa110",
  organization: "#d94800",
  event: "#dc2626",
  location: "#8b6914",
  statute: "#2563eb",
  content: "#6b7280",
  method: "#8b6914",
  data: "#a0a0a0",
  artifact: "#16a34a",
};
```

- [ ] **Step 2: Update component signature and add mode-dependent constants**

Replace the component function signature and add mode-dependent logic right after the component function opens:

```typescript
export default function GraphViewer({ nodes, edges, selectedNodeId, onNodeClick, searchTerm, mode = "full", focusNodeId }: GraphViewerProps) {
  const isMini = mode === "mini";
```

- [ ] **Step 3: Apply mini mode to simulation forces**

In the simulation setup (around line 109), replace the force configuration:

```typescript
    const simulation = forceSimulation<SimNode>(simNodes)
      .force("link", forceLink<SimNode, SimLink>(simLinks).id((d) => d.id).distance(isMini ? 40 : 60))
      .force("charge", forceManyBody().strength(isMini ? -60 : -120))
      .force("center", forceCenter(w / 2, h / 2).strength(isMini ? 0.3 : 0.1))
      .force("collide", forceCollide<SimNode>().radius((d) => getRadius(d.id) + 2))
      .alphaDecay(isMini ? 0.05 : 0.02)
      .velocityDecay(0.3);
```

- [ ] **Step 4: Apply mini mode to node rendering**

In both paint functions (the `paint` closure and the selection/search repaint effect), update the node label rendering condition and font size. Replace the label-drawing block:

```typescript
        const degree = degreeMap.get(node.id) ?? 1;
        const showLabel = isMini ? (isSelected || isHovered) : (degree >= 3 || isSelected || isMatch || isHovered);
        if (showLabel) {
          const fontSize = isMini ? 10 : Math.max(3, radius * 0.8);
          ctx.font = `${isSelected ? "bold " : ""}${fontSize}px sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          ctx.fillStyle = dimmed ? "#1f1f1f33" : "#1f1f1f";
          ctx.fillText(node.id, node.x, node.y! + radius + 2);
        }
```

- [ ] **Step 5: Disable pan/zoom in mini mode**

In the event handlers, wrap panning and zooming with mode checks. Replace `handleMouseDown` panning branch:

```typescript
      } else {
        if (!isMini) {
          isPanning = true;
          panStart = { x: e.clientX - transformRef.current.x, y: e.clientY - transformRef.current.y };
        }
      }
```

And wrap `handleWheel` body:

```typescript
    const handleWheel = (e: WheelEvent) => {
      if (isMini) return;
      e.preventDefault();
      // ... rest unchanged
    };
```

- [ ] **Step 6: Add focusNodeId effect**

Add a new `useEffect` at the end of the component, before the return statement:

```typescript
  // Focus + pulse animation when focusNodeId changes
  useEffect(() => {
    if (!focusNodeId) return;
    const canvas = canvasRef.current;
    if (!canvas || simNodesRef.current.length === 0) return;

    const targetNode = simNodesRef.current.find((n) => n.id === focusNodeId);
    if (!targetNode || targetNode.x == null) return;

    // Pan to center the node
    const rect = canvas.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    const t = transformRef.current;
    t.x = w / 2 - targetNode.x * t.k;
    t.y = h / 2 - targetNode.y! * t.k;

    // Pulse animation: 2 seconds
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let start: number | null = null;
    const duration = 2000;

    const animate = (timestamp: number) => {
      if (!start) start = timestamp;
      const elapsed = timestamp - start;
      if (elapsed > duration) return;
      const progress = elapsed / duration;
      const pulseRadius = getRadius(focusNodeId) + 20 * Math.sin(progress * Math.PI * 4) * (1 - progress);
      const alpha = 0.4 * (1 - progress);

      // Trigger a repaint by the existing effect (selection change)
      // Then overlay the pulse
      const { x: tx, y: ty, k } = transformRef.current;
      ctx.save();
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      ctx.translate(tx, ty);
      ctx.scale(k, k);
      ctx.beginPath();
      ctx.arc(targetNode.x!, targetNode.y!, pulseRadius, 0, 2 * Math.PI);
      ctx.strokeStyle = `rgba(250, 82, 15, ${alpha})`;
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.restore();

      requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [focusNodeId, getRadius]);
```

- [ ] **Step 7: Update container background for mini mode**

Replace the return JSX:

```typescript
  return (
    <div ref={containerRef} className="flex-1 relative" style={{ background: isMini ? "transparent" : "#fef9ef" }} data-testid="graph-viewer">
      <canvas ref={canvasRef} className="absolute inset-0" />
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center" style={{ color: "var(--color-text-muted)" }}>
          No nodes to display
        </div>
      )}
    </div>
  );
```

- [ ] **Step 8: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven-ui/src/components/GraphViewer.tsx
git commit -m "feat(ui): add mode and focusNodeId props to GraphViewer"
```

---

### Task 5: Frontend — MiniGraph component

**Files:**
- Create: `openraven-ui/src/components/MiniGraph.tsx`

- [ ] **Step 1: Create MiniGraph.tsx**

```typescript
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";
import GraphViewer, { type GraphNode } from "./GraphViewer";

interface MiniGraphProps {
  sourceFiles: string[];
  height?: number;
}

interface FloatingCard {
  node: GraphNode;
  x: number;
  y: number;
}

const TYPE_LABELS: Record<string, string> = {
  concept: "概念", content: "內容", organization: "組織", person: "人物",
  method: "方法", data: "數據", event: "判決/事件", statute: "法條",
  artifact: "文件", location: "地點", technology: "技術",
};

export default function MiniGraph({ sourceFiles, height = 280 }: MiniGraphProps) {
  const { t, i18n } = useTranslation("graph");
  const { isDemo } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState<{ nodes: GraphNode[]; edges: any[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [card, setCard] = useState<FloatingCard | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (sourceFiles.length === 0) return;
    setLoading(true);
    const fileNames = sourceFiles.map((f) => f.split("/").pop() || f);
    const unique = [...new Set(fileNames)];
    fetch(`/api/graph/subgraph?files=${encodeURIComponent(unique.join(","))}&max_nodes=30`)
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [sourceFiles]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedId(node.id);
    setCard({ node, x: 0, y: 0 });
  }, []);

  const handleNavigate = useCallback(
    (nodeId: string) => {
      const prefix = isDemo ? "/demo" : "";
      navigate(`${prefix}/graph?highlight=${encodeURIComponent(nodeId)}`);
    },
    [isDemo, navigate],
  );

  if (loading) return <div className="text-xs py-4" style={{ color: "var(--color-text-muted)" }}>{t("loadingGraph")}</div>;
  if (!data || data.nodes.length < 2) return null;

  const isChinese = i18n.language?.startsWith("zh");

  return (
    <div className="relative" style={{ height }}>
      <GraphViewer
        nodes={data.nodes}
        edges={data.edges}
        selectedNodeId={selectedId}
        onNodeClick={handleNodeClick}
        searchTerm=""
        mode="mini"
      />
      {card && (
        <div
          className="absolute bottom-2 left-2 right-2 p-3"
          style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)", zIndex: 10 }}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs uppercase tracking-wider px-1.5 py-0.5" style={{ background: "var(--bg-surface-warm)", color: "var(--color-text-secondary)" }}>
              {isChinese
                ? TYPE_LABELS[card.node.properties?.entity_type] || card.node.properties?.entity_type || "unknown"
                : card.node.properties?.entity_type || "unknown"}
            </span>
            <button onClick={() => setCard(null)} className="text-xs cursor-pointer" style={{ color: "var(--color-text-muted)" }}>✕</button>
          </div>
          <div className="text-sm font-medium mb-1" style={{ color: "var(--color-text)" }}>{card.node.id}</div>
          <div className="text-xs mb-2 line-clamp-2" style={{ color: "var(--color-text-secondary)" }}>
            {(card.node.properties?.description || "").split("<SEP>")[0].slice(0, 100)}
          </div>
          <button
            onClick={() => handleNavigate(card.node.id)}
            className="text-xs cursor-pointer hover:opacity-80"
            style={{ color: "var(--color-brand)" }}
          >
            {t("viewInGraph")} →
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven-ui/src/components/MiniGraph.tsx
git commit -m "feat(ui): add MiniGraph component for embedded subgraph visualization"
```

---

### Task 6: Frontend — AskPage embed MiniGraph

**Files:**
- Modify: `openraven-ui/src/pages/AskPage.tsx`

- [ ] **Step 1: Add MiniGraph import and state**

At the top of `openraven-ui/src/pages/AskPage.tsx`, add import:

```typescript
import MiniGraph from "../components/MiniGraph";
```

Inside the component function, add state for expand/collapse:

```typescript
  const [showMiniGraph, setShowMiniGraph] = useState(false);
```

- [ ] **Step 2: Add MiniGraph section after sources**

In the JSX, find the sources block (around line 141-151). After the closing `</div>` of the sources section (the one with `borderLeft` style), add the MiniGraph toggle and component:

```typescript
              {msg.sources && msg.sources.length > 0 && (
                <div className="ml-4 mt-1 mb-2 pl-3" style={{ borderLeft: "2px solid var(--color-border)" }}>
                  <div className="text-xs mb-1" style={{ color: "var(--color-text-muted)" }}>{t('sourcesCount', { count: msg.sources.length })}</div>
                  {msg.sources.map((s, j) => (
                    <div key={j} className="text-xs mb-0.5" style={{ color: "var(--color-text-secondary)" }}>
                      <span style={{ color: "var(--color-brand)" }}>{s.document}</span>
                      {s.excerpt && <span className="ml-2" style={{ color: "var(--color-text-muted)" }}>— {s.excerpt}</span>}
                    </div>
                  ))}
                  <button
                    onClick={() => setShowMiniGraph((prev) => !prev)}
                    className="text-xs mt-2 cursor-pointer hover:opacity-80"
                    style={{ color: "var(--color-brand)" }}
                  >
                    {showMiniGraph ? "▲" : "▼"} {t('expandMiniGraph', { ns: 'graph' })}
                  </button>
                  {showMiniGraph && (
                    <div className="mt-2" style={{ border: "1px solid var(--color-border)" }}>
                      <MiniGraph sourceFiles={msg.sources.map((s) => s.document)} />
                    </div>
                  )}
                </div>
              )}
```

Note: This replaces the existing sources block entirely — the sources list is preserved as-is, with the MiniGraph toggle and component appended at the bottom.

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven-ui/src/pages/AskPage.tsx
git commit -m "feat(ui): embed MiniGraph in AskPage below answer sources"
```

---

### Task 7: Frontend — GraphNodeDetail upgrade

**Files:**
- Modify: `openraven-ui/src/components/GraphNodeDetail.tsx`

- [ ] **Step 1: Rewrite GraphNodeDetail.tsx**

Replace the entire content of `openraven-ui/src/components/GraphNodeDetail.tsx`:

```typescript
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";

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
  event: "#dc2626",
  location: "#8b6914",
  statute: "#2563eb",
  content: "#6b7280",
  method: "#8b6914",
  data: "#a0a0a0",
  artifact: "#16a34a",
};

const TYPE_LABELS: Record<string, string> = {
  concept: "概念", content: "內容", organization: "組織", person: "人物",
  method: "方法", data: "數據", event: "判決/事件", statute: "法條",
  artifact: "文件", location: "地點", technology: "技術",
};

const RELATION_LABELS: Record<string, string> = {
  requirement: "要求", "legal basis": "依據", "governed by": "規範",
  "issued by": "作出", covers: "承保", component: "包含",
  "type of": "屬於", party: "當事人", "court ruling": "判決",
};

function extractRelationLabel(keywords: string): string {
  const kw = keywords.toLowerCase();
  for (const [key, label] of Object.entries(RELATION_LABELS)) {
    if (kw.includes(key)) return label;
  }
  return "關聯";
}

interface Excerpt {
  file: string;
  text: string;
  line_start: number;
  line_end: number;
}

export default function GraphNodeDetail({ node, neighbors, edges, onClose, onNavigate }: GraphNodeDetailProps) {
  const { t, i18n } = useTranslation("graph");
  const { isDemo } = useAuth();
  const navigate = useNavigate();
  const [excerpts, setExcerpts] = useState<Excerpt[]>([]);
  const [contextFiles, setContextFiles] = useState<string[]>([]);
  const [loadingContext, setLoadingContext] = useState(false);

  useEffect(() => {
    if (!node) return;
    setLoadingContext(true);
    setExcerpts([]);
    setContextFiles([]);
    fetch(`/api/graph/node/${encodeURIComponent(node.id)}/context`)
      .then((r) => r.json())
      .then((data) => {
        setExcerpts(data.excerpts || []);
        setContextFiles(data.files || []);
        setLoadingContext(false);
      })
      .catch(() => setLoadingContext(false));
  }, [node?.id]);

  const handleAsk = useCallback(() => {
    if (!node) return;
    const prefix = isDemo ? "/demo" : "";
    const q = encodeURIComponent(`請說明「${node.id}」的相關規定`);
    navigate(`${prefix}/ask?q=${q}`);
  }, [node, isDemo, navigate]);

  if (!node) return null;
  const edgeList = edges ?? [];
  const entityType = node.properties.entity_type ?? node.labels[0] ?? "unknown";
  const description = (node.properties.description ?? "").split("<SEP>")[0];
  const typeColor = TYPE_COLORS[entityType] ?? "var(--color-text-muted)";
  const isChinese = i18n.language?.startsWith("zh");
  const typeLabel = isChinese ? TYPE_LABELS[entityType] || entityType : entityType;

  // Parse multi-file from file_path (SEP-separated)
  const rawFilePath = node.properties.file_path ?? "";
  const filePaths = rawFilePath
    .split("<SEP>")
    .map((p: string) => p.trim().split("/").pop() || p.trim())
    .filter((p: string) => p);
  const uniqueFiles = [...new Set([...filePaths, ...contextFiles])];

  return (
    <div className="w-80 p-4 overflow-y-auto" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-golden)" }}>
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs uppercase tracking-wider px-2 py-0.5" style={{ background: "var(--bg-surface-warm)", color: typeColor }}>
          {typeLabel}
        </span>
        <button onClick={onClose} aria-label="Close" className="text-sm cursor-pointer hover:opacity-70 p-1" style={{ color: "var(--color-text-muted)" }}>✕</button>
      </div>
      <h2 className="text-2xl mb-3" style={{ color: "var(--color-text)", lineHeight: 1.33 }}>{node.id}</h2>
      {description && (
        <p className="text-sm mb-4 leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{description}</p>
      )}

      {/* Excerpts */}
      {loadingContext ? (
        <div className="mb-4 text-xs animate-pulse" style={{ color: "var(--color-text-muted)" }}>{t("loadingContext")}</div>
      ) : excerpts.length > 0 ? (
        <div className="mb-4">
          <h3 className="text-xs uppercase tracking-wider mb-2" style={{ color: "var(--color-text-muted)" }}>{t("excerptHeading")}</h3>
          {excerpts.map((ex, i) => (
            <div key={i} className="text-xs mb-2 p-2 leading-relaxed" style={{ background: "var(--bg-surface-warm)", color: "var(--color-text-secondary)" }}>
              <pre className="whitespace-pre-wrap font-sans">{ex.text}</pre>
              <div className="mt-1 text-xs" style={{ color: "var(--color-text-muted)" }}>— {ex.file}</div>
            </div>
          ))}
        </div>
      ) : null}

      {/* Multi-file sources */}
      {uniqueFiles.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs uppercase tracking-wider mb-2" style={{ color: "var(--color-text-muted)" }}>
            {t("appearsIn", { count: uniqueFiles.length })}
          </h3>
          {uniqueFiles.map((f, i) => (
            <div key={i} className="text-xs mb-0.5" style={{ color: "var(--color-text-secondary)" }}>📄 {f}</div>
          ))}
        </div>
      )}

      {/* Relations */}
      {neighbors.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs uppercase tracking-wider mb-2" style={{ color: "var(--color-text-muted)" }}>
            {t("relatedCount", { count: neighbors.length })}
          </h3>
          <div className="flex flex-col gap-2">
            {neighbors.map((n) => {
              const edge = edgeList.find((e) => e.target === n.id);
              const label = edge ? (isChinese ? extractRelationLabel(edge.keywords) : "") : "";
              return (
                <div key={n.id} className="p-2" style={{ background: "var(--bg-surface-hover)", boxShadow: "var(--shadow-subtle)" }}>
                  <div className="flex items-center gap-2">
                    {label && <span className="text-xs px-1" style={{ color: "var(--color-text-muted)" }}>{label}→</span>}
                    <button
                      onClick={() => onNavigate(n.id)}
                      className="text-left text-sm truncate block cursor-pointer hover:opacity-70"
                      style={{ color: "var(--color-brand)" }}
                    >
                      {n.id}
                    </button>
                  </div>
                  {edge?.description && (
                    <p className="text-xs mt-0.5 ml-2" style={{ color: "var(--color-text-muted)" }}>{edge.description.split("<SEP>")[0].slice(0, 80)}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleAsk}
          className="text-xs px-3 py-1.5 cursor-pointer hover:opacity-80"
          style={{ background: "var(--color-brand)", color: "var(--color-text-on-brand)" }}
        >
          {t("askAbout")}
        </button>
        <button
          onClick={() => {
            const prefix = isDemo ? "/demo" : "";
            navigate(`${prefix}/wiki`);
          }}
          className="text-xs px-3 py-1.5 cursor-pointer hover:opacity-80"
          style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}
        >
          {t("viewWiki")}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven-ui/src/components/GraphNodeDetail.tsx
git commit -m "feat(ui): upgrade GraphNodeDetail with context excerpts, multi-source, action buttons"
```

---

### Task 8: Frontend — GraphPage dynamic filters + guide + highlight

**Files:**
- Modify: `openraven-ui/src/pages/GraphPage.tsx`

- [ ] **Step 1: Replace ENTITY_TYPES with dynamic types and add URL highlight**

Replace the entire content of `openraven-ui/src/pages/GraphPage.tsx`:

```typescript
import { useEffect, useState, useMemo, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import GraphViewer, { type GraphNode, type GraphEdge } from "../components/GraphViewer";
import GraphNodeDetail from "../components/GraphNodeDetail";

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  is_truncated: boolean;
}

const TYPE_LABELS: Record<string, string> = {
  concept: "概念", content: "內容", organization: "組織", person: "人物",
  method: "方法", data: "數據", event: "判決/事件", statute: "法條",
  artifact: "文件", location: "地點", technology: "技術",
};

export default function GraphPage() {
  const { t, i18n } = useTranslation("graph");
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get("highlight");

  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeTypes, setActiveTypes] = useState<Set<string> | null>(null);
  const [minDegree, setMinDegree] = useState(0);
  const [focusNodeId, setFocusNodeId] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/graph?max_nodes=500")
      .then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      })
      .then((d) => {
        setData(d);
        setLoading(false);
        // Initialize activeTypes from actual data
        const types = new Set(d.nodes.map((n: GraphNode) => n.properties?.entity_type ?? n.labels[0] ?? "unknown"));
        setActiveTypes(types);
      })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, []);

  // Handle URL highlight parameter after data loads
  useEffect(() => {
    if (!highlightId || !data) return;
    const exact = data.nodes.find((n) => n.id === highlightId);
    const match = exact || data.nodes.find((n) => n.id.includes(highlightId));
    if (match) {
      setSelectedNode(match);
      setFocusNodeId(match.id);
    }
  }, [highlightId, data]);

  const typeCounts = useMemo(() => {
    if (!data) return new Map<string, number>();
    const counts = new Map<string, number>();
    for (const n of data.nodes) {
      const type = n.properties?.entity_type ?? n.labels[0] ?? "unknown";
      counts.set(type, (counts.get(type) ?? 0) + 1);
    }
    return counts;
  }, [data]);

  const sortedTypes = useMemo(() => {
    return [...typeCounts.entries()].sort((a, b) => b[1] - a[1]).map(([type]) => type);
  }, [typeCounts]);

  const filteredNodes = useMemo(() => {
    if (!data || !activeTypes) return [];
    const typeFilteredNodeIds = new Set(
      data.nodes.filter((n) => {
        const type = n.properties?.entity_type ?? n.labels[0] ?? "unknown";
        return activeTypes.has(type);
      }).map((n) => n.id),
    );
    const typeFilteredEdges = data.edges.filter(
      (e) => typeFilteredNodeIds.has(e.source) && typeFilteredNodeIds.has(e.target),
    );
    const degrees = new Map<string, number>();
    for (const e of typeFilteredEdges) {
      degrees.set(e.source, (degrees.get(e.source) ?? 0) + 1);
      degrees.set(e.target, (degrees.get(e.target) ?? 0) + 1);
    }
    return data.nodes.filter((n) => {
      const type = n.properties?.entity_type ?? n.labels[0] ?? "unknown";
      if (!activeTypes.has(type)) return false;
      if (minDegree > 0 && (degrees.get(n.id) ?? 0) < minDegree) return false;
      return true;
    });
  }, [data, activeTypes, minDegree]);

  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const filteredEdges = useMemo(() => {
    if (!data) return [];
    return data.edges.filter((e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target));
  }, [data, filteredNodeIds]);

  useEffect(() => {
    if (selectedNode && !filteredNodeIds.has(selectedNode.id)) setSelectedNode(null);
  }, [filteredNodeIds, selectedNode]);

  const neighbors = useMemo(() => {
    if (!selectedNode || !data) return [];
    const id = selectedNode.id;
    const neighborIds = new Set<string>();
    for (const e of data.edges) {
      if (e.source === id) neighborIds.add(e.target);
      if (e.target === id) neighborIds.add(e.source);
    }
    return data.nodes.filter((n) => neighborIds.has(n.id)).map((n) => ({ id: n.id, labels: n.labels }));
  }, [selectedNode, data]);

  const selectedEdges = useMemo(() => {
    if (!selectedNode || !data) return [];
    const id = selectedNode.id;
    return data.edges
      .filter((e) => e.source === id || e.target === id)
      .map((e) => ({
        target: e.source === id ? e.target : e.source,
        description: e.properties?.description ?? "",
        keywords: e.properties?.keywords ?? "",
      }));
  }, [selectedNode, data]);

  const handleNodeClick = useCallback((node: GraphNode) => { setSelectedNode(node); }, []);
  const handleNavigate = useCallback((nodeId: string) => {
    const node = data?.nodes.find((n) => n.id === nodeId);
    if (node) setSelectedNode(node);
  }, [data]);

  function exportPNG() {
    const canvas = document.querySelector('[data-testid="graph-viewer"] canvas') as HTMLCanvasElement;
    if (!canvas) return;
    const link = document.createElement("a");
    link.download = "openraven-knowledge-graph.png";
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  const toggleType = (type: string) => {
    setActiveTypes((prev) => {
      if (!prev) return prev;
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const isChinese = i18n.language?.startsWith("zh");

  if (loading) return <div className="p-8" style={{ color: "var(--color-text-muted)" }} data-testid="graph-loading">{t("loadingGraph")}</div>;
  if (error) return <div className="p-8" style={{ color: "var(--color-error)" }} data-testid="graph-error">Error: {error}</div>;
  if (!data || data.nodes.length === 0) {
    return (
      <div className="p-8" style={{ color: "var(--color-text-muted)" }} data-testid="graph-empty">
        <h1 className="text-3xl mb-2" style={{ color: "var(--color-text)", lineHeight: 1.15 }}>{t("title")}</h1>
        <p>{t("emptyMessage")}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Guide summary */}
      <div className="px-4 py-2 text-xs" style={{ background: "var(--bg-surface-warm)", color: "var(--color-text-secondary)", borderBottom: "1px solid var(--color-border)" }}>
        {t("guideSummary", { nodes: data.nodes.length, edges: data.edges.length })}
      </div>
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 flex-wrap" style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-subtle)", borderBottom: "1px solid var(--color-border)" }}>
        <input
          type="text"
          placeholder={t("searchPlaceholder")}
          aria-label={t("searchPlaceholder")}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
        />
        <div className="flex gap-1 flex-wrap">
          {sortedTypes.map((type) => (
            <button
              key={type}
              onClick={() => toggleType(type)}
              className="text-xs px-2.5 py-1.5 cursor-pointer"
              style={
                activeTypes?.has(type)
                  ? { background: "var(--color-brand)", color: "var(--color-text-on-brand)" }
                  : { background: "var(--bg-surface-warm)", color: "var(--color-text-secondary)" }
              }
            >
              {isChinese ? TYPE_LABELS[type] || type : type} {typeCounts.get(type)}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs" style={{ color: "var(--color-text-muted)" }}>{t("minConnections")}</label>
          <input type="range" min={0} max={10} value={minDegree} onChange={(e) => setMinDegree(Number(e.target.value))} className="w-20 h-1" style={{ accentColor: "var(--color-brand)" }} />
          <span className="text-xs w-4" style={{ color: "var(--color-text-secondary)" }}>{minDegree}</span>
        </div>
        <a href="/api/graph/export" download className="text-xs px-2.5 py-1.5 uppercase cursor-pointer" style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>{t("exportGraphML")}</a>
        <button onClick={exportPNG} className="text-xs px-2.5 py-1.5 uppercase cursor-pointer" style={{ background: "var(--color-dark)", color: "var(--color-text-on-brand)" }}>{t("exportPNG")}</button>
        <span className="text-xs ml-auto" style={{ color: "var(--color-text-muted)" }}>
          {filteredNodes.length} nodes / {filteredEdges.length} edges
          {data.is_truncated && ` ${t("truncated", { ns: "common" })}`}
        </span>
      </div>
      {/* Graph + Detail panel */}
      <div className="flex flex-1 min-h-0">
        <GraphViewer
          nodes={filteredNodes}
          edges={filteredEdges}
          selectedNodeId={selectedNode?.id ?? null}
          onNodeClick={handleNodeClick}
          searchTerm={searchTerm}
          focusNodeId={focusNodeId}
        />
        {selectedNode && (
          <GraphNodeDetail
            node={selectedNode}
            neighbors={neighbors}
            edges={selectedEdges}
            onClose={() => setSelectedNode(null)}
            onNavigate={handleNavigate}
          />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven-ui/src/pages/GraphPage.tsx
git commit -m "feat(ui): GraphPage dynamic entity filters, guide bar, URL highlight support"
```

---

### Task 9: i18n — add new keys to all 12 locales

**Files:**
- Modify: `openraven-ui/public/locales/*/graph.json` (12 files)

- [ ] **Step 1: Update English graph.json**

Replace `openraven-ui/public/locales/en/graph.json`:

```json
{
  "title": "Knowledge Graph",
  "loadingGraph": "Loading graph...",
  "searchPlaceholder": "Search nodes...",
  "minConnections": "Min connections:",
  "exportGraphML": "Export GraphML",
  "exportPNG": "Export PNG",
  "emptyMessage": "No graph data yet. Add files to start building your knowledge graph.",
  "source": "Source",
  "connectedCount": "Connected ({{count}})",
  "guideSummary": "This knowledge base contains {{nodes}} entities and {{edges}} relations. Click a node for details, or use filters to focus on specific types.",
  "expandMiniGraph": "Related Graph",
  "viewInGraph": "View in graph",
  "askAbout": "Ask OpenRaven",
  "viewWiki": "View Wiki",
  "excerptHeading": "Original Text",
  "appearsIn": "Appears in {{count}} files",
  "viewFullDocument": "View full document",
  "relatedCount": "Related ({{count}})",
  "loadingContext": "Loading context...",
  "entityNotFound": "Entity not found"
}
```

- [ ] **Step 2: Update zh-TW graph.json**

Replace `openraven-ui/public/locales/zh-TW/graph.json`:

```json
{
  "title": "知識圖譜",
  "loadingGraph": "載入圖譜中...",
  "searchPlaceholder": "搜尋節點...",
  "minConnections": "最少連線數：",
  "exportGraphML": "匯出 GraphML",
  "exportPNG": "匯出 PNG",
  "emptyMessage": "尚無圖譜資料。新增檔案以開始建立您的知識圖譜。",
  "source": "來源",
  "connectedCount": "已連線 ({{count}})",
  "guideSummary": "此知識庫包含 {{nodes}} 個實體、{{edges}} 條關聯。點擊節點查看詳情與原文，或使用篩選器聚焦特定類型。",
  "expandMiniGraph": "關聯圖譜",
  "viewInGraph": "在圖譜中查看",
  "askAbout": "問 OpenRaven",
  "viewWiki": "查看 Wiki",
  "excerptHeading": "原文摘錄",
  "appearsIn": "出現在 {{count}} 份文件",
  "viewFullDocument": "查看完整文件",
  "relatedCount": "關聯 ({{count}})",
  "loadingContext": "載入原文中...",
  "entityNotFound": "找不到該實體"
}
```

- [ ] **Step 3: Update zh-CN graph.json**

Replace `openraven-ui/public/locales/zh-CN/graph.json`:

```json
{
  "title": "知识图谱",
  "loadingGraph": "加载图谱中...",
  "searchPlaceholder": "搜索节点...",
  "minConnections": "最少连接数：",
  "exportGraphML": "导出 GraphML",
  "exportPNG": "导出 PNG",
  "emptyMessage": "暂无图谱数据。添加文件以开始构建您的知识图谱。",
  "source": "来源",
  "connectedCount": "已连接 ({{count}})",
  "guideSummary": "此知识库包含 {{nodes}} 个实体、{{edges}} 条关联。点击节点查看详情与原文，或使用筛选器聚焦特定类型。",
  "expandMiniGraph": "关联图谱",
  "viewInGraph": "在图谱中查看",
  "askAbout": "问 OpenRaven",
  "viewWiki": "查看 Wiki",
  "excerptHeading": "原文摘录",
  "appearsIn": "出现在 {{count}} 份文件",
  "viewFullDocument": "查看完整文件",
  "relatedCount": "关联 ({{count}})",
  "loadingContext": "加载原文中...",
  "entityNotFound": "找不到该实体"
}
```

- [ ] **Step 4: Update remaining 9 locale files with English fallback keys**

For each of `ja`, `ko`, `fr`, `es`, `nl`, `it`, `vi`, `th`, `ru`, add the same new keys using English values (they already have the base keys; just append the new ones). Run this script:

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui/public/locales
for locale in ja ko fr es nl it vi th ru; do
  python3 -c "
import json, sys
with open('$locale/graph.json', 'r') as f:
    data = json.load(f)
new_keys = {
    'guideSummary': 'This knowledge base contains {{nodes}} entities and {{edges}} relations. Click a node for details, or use filters to focus on specific types.',
    'expandMiniGraph': 'Related Graph',
    'viewInGraph': 'View in graph',
    'askAbout': 'Ask OpenRaven',
    'viewWiki': 'View Wiki',
    'excerptHeading': 'Original Text',
    'appearsIn': 'Appears in {{count}} files',
    'viewFullDocument': 'View full document',
    'relatedCount': 'Related ({{count}})',
    'loadingContext': 'Loading context...',
    'entityNotFound': 'Entity not found',
}
for k, v in new_keys.items():
    if k not in data:
        data[k] = v
with open('$locale/graph.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write('\n')
"
done
```

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven-ui/public/locales/*/graph.json
git commit -m "feat(i18n): add knowledge graph UX enhancement keys to all 12 locales"
```

---

### Task 10: Integration verification

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

```bash
cd /home/ubuntu/source/OpenRaven/openraven
source .venv/bin/activate
pytest tests/test_graph.py tests/test_api.py -v
```

Expected: All PASS

- [ ] **Step 2: Verify frontend builds without errors**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui
bun run build
```

Expected: Build succeeds with no TypeScript errors

- [ ] **Step 3: Test new APIs against live data**

```bash
# Subgraph API
curl -s "http://localhost:8741/api/graph/subgraph?files=pdpa-個資法.md&max_nodes=10" -b /tmp/legal-cookie.txt | python3 -m json.tool | head -20

# Node context API
curl -s "http://localhost:8741/api/graph/node/個資法第27條/context" -b /tmp/legal-cookie.txt | python3 -m json.tool
```

Expected: Both return valid JSON with nodes/edges and excerpts respectively

- [ ] **Step 4: Start dev server and test in browser**

```bash
cd /home/ubuntu/source/OpenRaven/openraven-ui
bun run dev
```

Test scenarios:
1. Open `/demo` → select 台灣法律文件 → ask a question → expand MiniGraph below sources
2. Click a node in MiniGraph → see floating card → click "在圖譜中查看"
3. Land on `/demo/graph?highlight=...` → node auto-selected + pulsing animation
4. Graph page: verify dynamic entity type filters with counts
5. Graph page: click node → detail panel shows original text excerpt + multi-file sources + action buttons
6. Click "問 OpenRaven" button → navigate to Ask page with prefilled query

- [ ] **Step 5: Final commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add -A
git status
# Only commit if there are remaining changes
git commit -m "chore: integration verification cleanup"
```
