# Knowledge Graph Visualization Implementation Plan (v2 — post-review)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an interactive knowledge graph visualization page to OpenRaven's web UI, exposing the LightRAG graph as a navigable, force-directed node-link diagram with search, filtering, and node detail inspection.

**Architecture:** New `/api/graph` endpoint on FastAPI reads the NetworkX GraphML file and returns JSON nodes+edges. Hono BFF proxies it. A new `/graph` route in the React SPA renders the graph using direct `d3-force` simulation + HTML5 Canvas (no wrapper library — avoids React 19 incompatibility with `react-force-graph-2d`). The graph canvas is full-width (breaks out of the existing `max-w-4xl` constraint). Nodes are colored by `entity_type`, sized by degree. Clicking a node shows a detail panel with description, source document, and connected entities.

**Tech Stack:**
- Python: FastAPI + NetworkX (already installed) — new endpoint, no new Python deps
- TypeScript: `d3-force` + `d3-quadtree` (MIT, ~30KB total) — direct Canvas2D rendering
- Styling: Tailwind v4 (existing)

**PRD Alignment:**
- This implements "基本知識圖譜視覺化" (P1, open-source tier)
- PRD acceptance: >50 nodes rendered, link accuracy >85%
- "Advanced interactive" features (clustering, timeline, etc.) are deferred to commercial tier per PRD

**Review fixes applied (v2):**
- C1: `description` not `entity_description` — LightRAG stores `description` in GraphML
- C2: Direct `d3-force` + canvas instead of `react-force-graph-2d` (React 19 incompatible)
- C3: Single `<Routes>` tree in App.tsx with conditional className
- W1: `file_path` for human-readable source display, fallback to `source_id`
- W2: `run_in_executor` for blocking `nx.read_graphml()` in async endpoint
- W3: `try/except` around GraphML parse for race condition during ingestion
- W4: Clear `selectedNode` when type-filtered out
- W5: `useMemo` for degreeMap instead of `useRef` + `useEffect`
- W6: Deep-copy edges before passing to D3 to prevent mutation
- W7: Flexbox layout instead of magic `57px` nav height
- I1: Added `GraphPage` empty/error state tests
- I2: `Query(ge=1, le=5000)` validation on `max_nodes`

---

## File Structure

### Python backend (openraven/)

| File | Action | Responsibility |
|---|---|---|
| `src/openraven/graph/rag.py` | Modify | Add `get_graph_data()` method to `RavenGraph` |
| `src/openraven/api/server.py` | Modify | Add `GET /api/graph` endpoint with query params |
| `tests/test_graph.py` | Modify | Add tests for `get_graph_data()` |
| `tests/test_api.py` | Modify | Add test for `/api/graph` endpoint |

### TypeScript frontend (openraven-ui/)

| File | Action | Responsibility |
|---|---|---|
| `package.json` | Modify | Add `d3-force` + `d3-quadtree` + `@types/d3-force` dependencies |
| `server/services/core-client.ts` | Modify | Add `getGraphData()` proxy function + types |
| `server/routes/graph.ts` | Create | Hono route proxying to core `/api/graph` |
| `server/index.ts` | Modify | Register graph route |
| `src/App.tsx` | Modify | Add `/graph` route + nav link, conditional full-width |
| `src/pages/GraphPage.tsx` | Create | Page: fetches graph data, renders viewer + controls |
| `src/components/GraphViewer.tsx` | Create | D3-force canvas with zoom/pan |
| `src/components/GraphNodeDetail.tsx` | Create | Side panel showing selected node properties |
| `tests/server/routes.test.ts` | Modify | Add graph route tests |
| `tests/components/GraphViewer.test.tsx` | Create | Component test for GraphViewer |
| `tests/components/GraphPage.test.tsx` | Create | Page test for empty/error states |

---

## Task 1: Python — `get_graph_data()` method on RavenGraph

**Files:**
- Modify: `openraven/src/openraven/graph/rag.py`
- Modify: `openraven/tests/test_graph.py`

- [ ] **Step 1: Write failing tests for `get_graph_data()`**

Add to `openraven/tests/test_graph.py`:

```python
def test_get_graph_data_empty(graph: RavenGraph) -> None:
    data = graph.get_graph_data()
    assert data["nodes"] == []
    assert data["edges"] == []
    assert data["is_truncated"] is False


def test_get_graph_data_with_graphml(graph: RavenGraph) -> None:
    import networkx as nx

    # Create a small test graph — use "description" (not "entity_description")
    # because LightRAG's operate.py stores the attribute as "description"
    g = nx.Graph()
    g.add_node("KAFKA", entity_type="technology", description="Event streaming platform", file_path="adr.md")
    g.add_node("EDA", entity_type="concept", description="Event-driven architecture", file_path="adr.md")
    g.add_edge("KAFKA", "EDA", weight="1.0", description="Kafka implements EDA", keywords="streaming,events")

    graph_file = graph.working_dir / "graph_chunk_entity_relation.graphml"
    nx.write_graphml(g, str(graph_file))

    data = graph.get_graph_data()
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    assert data["is_truncated"] is False

    node_ids = {n["id"] for n in data["nodes"]}
    assert "KAFKA" in node_ids
    assert "EDA" in node_ids

    # Verify properties use LightRAG's actual attribute names
    kafka_node = next(n for n in data["nodes"] if n["id"] == "KAFKA")
    assert kafka_node["properties"]["description"] == "Event streaming platform"
    assert kafka_node["properties"]["entity_type"] == "technology"
    assert kafka_node["labels"] == ["technology"]

    edge = data["edges"][0]
    assert edge["source"] in ("KAFKA", "EDA")
    assert edge["target"] in ("KAFKA", "EDA")
    assert "description" in edge["properties"]


def test_get_graph_data_respects_max_nodes(graph: RavenGraph) -> None:
    import networkx as nx

    g = nx.Graph()
    for i in range(10):
        g.add_node(f"NODE_{i}", entity_type="concept", description=f"Node {i}")
    # Connect all to NODE_0 so it has highest degree
    for i in range(1, 10):
        g.add_edge("NODE_0", f"NODE_{i}", weight="1.0", description=f"Edge to {i}")

    graph_file = graph.working_dir / "graph_chunk_entity_relation.graphml"
    nx.write_graphml(g, str(graph_file))

    data = graph.get_graph_data(max_nodes=3)
    assert len(data["nodes"]) == 3
    assert data["is_truncated"] is True
    # NODE_0 should be included (highest degree)
    node_ids = {n["id"] for n in data["nodes"]}
    assert "NODE_0" in node_ids


def test_get_graph_data_handles_corrupt_file(graph: RavenGraph) -> None:
    """Race condition: GraphML partially written during ingestion."""
    graph_file = graph.working_dir / "graph_chunk_entity_relation.graphml"
    graph_file.write_text("<graphml><graph><broken")

    data = graph.get_graph_data()
    assert data["nodes"] == []
    assert data["edges"] == []
    assert data["is_truncated"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_graph.py -v -k "get_graph_data"`
Expected: FAIL with `AttributeError: 'RavenGraph' object has no attribute 'get_graph_data'`

- [ ] **Step 3: Implement `get_graph_data()` on RavenGraph**

Add to `openraven/src/openraven/graph/rag.py`, after the `get_stats()` method:

```python
def get_graph_data(self, max_nodes: int = 500) -> dict:
    """Return graph nodes and edges as a JSON-serializable dict.

    Returns the top nodes by degree, with all edges between them.
    Format matches LightRAG's KnowledgeGraph schema.

    Note: reads graph_chunk_entity_relation.graphml directly from working_dir.
    This assumes LightRAG was initialized without a custom workspace prefix
    (same assumption as get_stats() and export_graphml()).
    """
    import networkx as nx

    graph_file = self.working_dir / "graph_chunk_entity_relation.graphml"
    if not graph_file.exists():
        return {"nodes": [], "edges": [], "is_truncated": False}

    try:
        graph = nx.read_graphml(str(graph_file))
    except Exception:
        # File may be partially written during concurrent ingestion
        return {"nodes": [], "edges": [], "is_truncated": False}

    total_nodes = graph.number_of_nodes()
    is_truncated = total_nodes > max_nodes

    # Take top nodes by degree
    if is_truncated:
        degrees = dict(graph.degree())
        sorted_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)
        limited = [n for n, _ in sorted_nodes[:max_nodes]]
        graph = graph.subgraph(limited)

    nodes = []
    for node_id, attrs in graph.nodes(data=True):
        nodes.append({
            "id": node_id,
            "labels": [attrs.get("entity_type", "unknown")],
            "properties": dict(attrs),
        })

    edges = []
    for source, target, attrs in graph.edges(data=True):
        edges.append({
            "id": f"{source}-{target}",
            "type": "DIRECTED",
            "source": source,
            "target": target,
            "properties": dict(attrs),
        })

    return {"nodes": nodes, "edges": edges, "is_truncated": is_truncated}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_graph.py -v -k "get_graph_data"`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven/src/openraven/graph/rag.py openraven/tests/test_graph.py
git commit -m "feat(graph): add get_graph_data() method to RavenGraph for visualization"
```

---

## Task 2: Python — `/api/graph` FastAPI endpoint

**Files:**
- Modify: `openraven/src/openraven/api/server.py`
- Modify: `openraven/tests/test_api.py`

- [ ] **Step 1: Write failing test for `/api/graph` endpoint**

Add to `openraven/tests/test_api.py`:

```python
def test_graph_endpoint(client: TestClient) -> None:
    response = client.get("/api/graph")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert "is_truncated" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_graph_endpoint_with_max_nodes(client: TestClient) -> None:
    response = client.get("/api/graph?max_nodes=10")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data


def test_graph_endpoint_rejects_invalid_max_nodes(client: TestClient) -> None:
    response = client.get("/api/graph?max_nodes=0")
    assert response.status_code == 422

    response = client.get("/api/graph?max_nodes=-1")
    assert response.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_api.py -v -k "graph"`
Expected: FAIL with 404 (route not found)

- [ ] **Step 3: Add `/api/graph` endpoint to server.py**

Add import at the top of `openraven/src/openraven/api/server.py`:

```python
import asyncio

from fastapi import FastAPI, File, Query, UploadFile
```

(Modify the existing `from fastapi import ...` line to add `Query` and add the `asyncio` import.)

After the `DiscoveryInsightResponse` model class, add:

```python
class GraphNodeResponse(BaseModel):
    id: str
    labels: list[str]
    properties: dict

class GraphEdgeResponse(BaseModel):
    id: str
    type: str
    source: str
    target: str
    properties: dict

class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    is_truncated: bool
```

Inside `create_app()`, after the `/api/discovery` route, add:

```python
@app.get("/api/graph", response_model=GraphResponse)
async def graph(max_nodes: int = Query(default=500, ge=1, le=5000)):
    # Run blocking NetworkX read in thread pool to avoid blocking event loop
    data = await asyncio.get_event_loop().run_in_executor(
        None, lambda: pipeline.graph.get_graph_data(max_nodes=max_nodes)
    )
    return GraphResponse(**data)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd openraven && .venv/bin/python -m pytest tests/test_api.py -v -k "graph"`
Expected: 3 tests PASS

- [ ] **Step 5: Run all Python tests to make sure nothing broke**

Run: `cd openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py`
Expected: All existing + new tests PASS

- [ ] **Step 6: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven/src/openraven/api/server.py openraven/tests/test_api.py
git commit -m "feat(api): add GET /api/graph endpoint for graph visualization data"
```

---

## Task 3: TypeScript — Hono proxy route + core-client function

**Files:**
- Modify: `openraven-ui/server/services/core-client.ts`
- Create: `openraven-ui/server/routes/graph.ts`
- Modify: `openraven-ui/server/index.ts`
- Modify: `openraven-ui/tests/server/routes.test.ts`

- [ ] **Step 1: Add types and `getGraphData()` to core-client.ts**

Add to `openraven-ui/server/services/core-client.ts` after the `DiscoveryInsight` interface:

```typescript
export interface GraphNode {
  id: string;
  labels: string[];
  properties: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  type: string;
  source: string;
  target: string;
  properties: Record<string, any>;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  is_truncated: boolean;
}

export async function getGraphData(maxNodes: number = 500): Promise<GraphResponse> {
  const res = await fetch(`${CORE_API_URL}/api/graph?max_nodes=${maxNodes}`);
  if (!res.ok) throw new Error(`Core API error: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 2: Create `server/routes/graph.ts`**

Create `openraven-ui/server/routes/graph.ts`:

```typescript
import { Hono } from "hono";
import { getGraphData } from "../services/core-client";

const graphRouter = new Hono();

graphRouter.get("/", async (c) => {
  try {
    const maxNodes = Number(c.req.query("max_nodes") ?? "500");
    const data = await getGraphData(maxNodes);
    return c.json(data);
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});

export default graphRouter;
```

- [ ] **Step 3: Register the graph route in `server/index.ts`**

Add import at the top of `openraven-ui/server/index.ts`:

```typescript
import graphRouter from "./routes/graph";
```

Add route registration after the discovery route:

```typescript
app.route("/api/graph", graphRouter);
```

- [ ] **Step 4: Write route tests**

Add to `openraven-ui/tests/server/routes.test.ts`:

In the mock setup section (before `mock.module()`), add:

```typescript
const mockGetGraphData = mock(async (_maxNodes: number) => ({
  nodes: [
    { id: "KAFKA", labels: ["technology"], properties: { entity_type: "technology", description: "Event streaming" } },
    { id: "EDA", labels: ["concept"], properties: { entity_type: "concept", description: "Event-driven architecture" } },
  ],
  edges: [
    { id: "KAFKA-EDA", type: "DIRECTED", source: "KAFKA", target: "EDA", properties: { weight: "1.0", description: "Implements" } },
  ],
  is_truncated: false,
}));
```

Inside the `mock.module()` call, add to the return object:

```typescript
getGraphData: mockGetGraphData,
```

Then add the test block:

```typescript
describe("GET /api/graph", () => {
  it("returns graph data with nodes and edges", async () => {
    const req = new Request("http://localhost/api/graph");
    const res = await appFetch(req);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.nodes)).toBe(true);
    expect(Array.isArray(body.edges)).toBe(true);
    expect(typeof body.is_truncated).toBe("boolean");
    expect(body.nodes.length).toBe(2);
    expect(body.edges.length).toBe(1);
  });

  it("passes max_nodes query param to core", async () => {
    const req = new Request("http://localhost/api/graph?max_nodes=10");
    const res = await appFetch(req);
    expect(res.status).toBe(200);
    expect(mockGetGraphData).toHaveBeenCalledWith(10);
  });

  it("returns 502 when core engine throws", async () => {
    mockGetGraphData.mockRejectedValueOnce(new Error("Core API error: 500"));
    const req = new Request("http://localhost/api/graph");
    const res = await appFetch(req);
    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body).toMatchObject({ error: expect.stringContaining("Core engine error") });
  });
});
```

- [ ] **Step 5: Run route tests**

Run: `cd openraven-ui && bun test tests/server/routes.test.ts`
Expected: All existing + 3 new graph tests PASS

- [ ] **Step 6: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven-ui/server/services/core-client.ts openraven-ui/server/routes/graph.ts openraven-ui/server/index.ts openraven-ui/tests/server/routes.test.ts
git commit -m "feat(ui): add graph proxy route and core-client function"
```

---

## Task 4: Install `d3-force` dependencies

**Files:**
- Modify: `openraven-ui/package.json`

> **Why not `react-force-graph-2d`?** That library internally uses `ReactDOM.render()` (the legacy React 17 API), which was removed in React 19. Since this project uses React 19, it would crash at runtime. Direct `d3-force` + Canvas2D gives us full control and zero compatibility risk.

- [ ] **Step 1: Install the dependencies**

```bash
cd openraven-ui && bun add d3-force d3-quadtree && bun add -d @types/d3-force @types/d3-quadtree
```

- [ ] **Step 2: Verify it installed correctly**

Run: `cd openraven-ui && bun run build`
Expected: Build succeeds without errors

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven-ui/package.json openraven-ui/bun.lockb
git commit -m "chore(ui): add d3-force and d3-quadtree dependencies"
```

---

## Task 5: React — `GraphNodeDetail` component

**Files:**
- Create: `openraven-ui/src/components/GraphNodeDetail.tsx`

This is built first because `GraphPage` depends on it, and it's independently testable.

- [ ] **Step 1: Create `GraphNodeDetail.tsx`**

Create `openraven-ui/src/components/GraphNodeDetail.tsx`:

```tsx
interface GraphNodeDetailProps {
  node: {
    id: string;
    labels: string[];
    properties: Record<string, any>;
  } | null;
  neighbors: { id: string; labels: string[] }[];
  onClose: () => void;
  onNavigate: (nodeId: string) => void;
}

const TYPE_COLORS: Record<string, string> = {
  technology: "text-blue-400",
  concept: "text-green-400",
  person: "text-amber-400",
  organization: "text-purple-400",
  event: "text-red-400",
  location: "text-cyan-400",
};

export default function GraphNodeDetail({ node, neighbors, onClose, onNavigate }: GraphNodeDetailProps) {
  if (!node) return null;

  const entityType = node.properties.entity_type ?? node.labels[0] ?? "unknown";
  // LightRAG stores "description" (not "entity_description") in GraphML
  const description = node.properties.description ?? "";
  // file_path is human-readable; source_id is chunk hashes (fallback)
  const source = node.properties.file_path ?? node.properties.source_id ?? "";
  const colorClass = TYPE_COLORS[entityType] ?? "text-gray-400";

  return (
    <div className="w-80 bg-gray-900 border-l border-gray-800 p-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <span className={`text-xs font-medium uppercase tracking-wider ${colorClass}`}>{entityType}</span>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-sm">✕</button>
      </div>
      <h2 className="text-lg font-bold text-white mb-3">{node.id}</h2>
      {description && (
        <p className="text-sm text-gray-400 mb-4 leading-relaxed">{description}</p>
      )}
      {source && (
        <div className="mb-4">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Source</h3>
          <p className="text-sm text-gray-400 break-all">{source}</p>
        </div>
      )}
      {neighbors.length > 0 && (
        <div>
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
            Connected ({neighbors.length})
          </h3>
          <div className="flex flex-col gap-1">
            {neighbors.map((n) => (
              <button
                key={n.id}
                onClick={() => onNavigate(n.id)}
                className="text-left text-sm text-blue-400 hover:text-blue-300 truncate"
              >
                {n.id}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven-ui/src/components/GraphNodeDetail.tsx
git commit -m "feat(ui): add GraphNodeDetail side panel component"
```

---

## Task 6: React — `GraphViewer` component (direct d3-force + Canvas2D)

**Files:**
- Create: `openraven-ui/src/components/GraphViewer.tsx`
- Create: `openraven-ui/tests/components/GraphViewer.test.tsx`

> **Design note:** We use `d3-force` directly with a `<canvas>` element managed via `useRef` + `useEffect`. This avoids the React 19 incompatibility of `react-force-graph-2d` and gives full control over rendering. The simulation runs in a `useEffect` cleanup cycle; the canvas repaints on each tick.

- [ ] **Step 1: Create `GraphViewer.tsx`**

Create `openraven-ui/src/components/GraphViewer.tsx`:

```tsx
import { useRef, useEffect, useMemo, useCallback } from "react";
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, type SimulationNodeDatum, type SimulationLinkDatum } from "d3-force";

export interface GraphNode {
  id: string;
  labels: string[];
  properties: Record<string, any>;
  // d3-force adds these at runtime
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface GraphEdge {
  id: string;
  type: string;
  source: string;
  target: string;
  properties: Record<string, any>;
}

// Internal types after d3 resolves string IDs to object refs
interface SimNode extends GraphNode, SimulationNodeDatum {}
interface SimLink extends SimulationLinkDatum<SimNode> {
  id: string;
  properties: Record<string, any>;
}

interface GraphViewerProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: string | null;
  onNodeClick: (node: GraphNode) => void;
  searchTerm: string;
}

const TYPE_COLORS: Record<string, string> = {
  technology: "#60a5fa", // blue-400
  concept: "#4ade80",    // green-400
  person: "#fbbf24",     // amber-400
  organization: "#c084fc", // purple-400
  event: "#f87171",      // red-400
  location: "#22d3ee",   // cyan-400
};
const DEFAULT_COLOR = "#9ca3af"; // gray-400

function getNodeColor(node: GraphNode): string {
  const type = node.properties?.entity_type ?? node.labels[0] ?? "unknown";
  return TYPE_COLORS[type] ?? DEFAULT_COLOR;
}

export default function GraphViewer({ nodes, edges, selectedNodeId, onNodeClick, searchTerm }: GraphViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  // Store simulation state in refs to avoid re-creating on every render
  const simNodesRef = useRef<SimNode[]>([]);
  const simLinksRef = useRef<SimLink[]>([]);
  const transformRef = useRef({ x: 0, y: 0, k: 1 });

  // Degree map computed synchronously (no stale-frame issue)
  const degreeMap = useMemo(() => {
    const m = new Map<string, number>();
    for (const edge of edges) {
      m.set(edge.source, (m.get(edge.source) ?? 0) + 1);
      m.set(edge.target, (m.get(edge.target) ?? 0) + 1);
    }
    return m;
  }, [edges]);

  const getRadius = useCallback((nodeId: string) => {
    const degree = degreeMap.get(nodeId) ?? 1;
    return Math.min(3 + Math.sqrt(degree) * 2, 16);
  }, [degreeMap]);

  // Main simulation + render effect
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container || nodes.length === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Size canvas to container
    const resize = () => {
      const rect = container.getBoundingClientRect();
      canvas.width = rect.width * devicePixelRatio;
      canvas.height = rect.height * devicePixelRatio;
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    };
    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);

    // Deep-copy nodes and edges so d3 mutation doesn't affect React state
    const simNodes: SimNode[] = nodes.map((n) => ({ ...n }));
    const simLinks: SimLink[] = edges.map((e) => ({
      source: e.source,
      target: e.target,
      id: e.id,
      properties: e.properties,
    }));
    simNodesRef.current = simNodes;
    simLinksRef.current = simLinks;

    const w = canvas.width / devicePixelRatio;
    const h = canvas.height / devicePixelRatio;

    const simulation = forceSimulation<SimNode>(simNodes)
      .force("link", forceLink<SimNode, SimLink>(simLinks).id((d) => d.id).distance(60))
      .force("charge", forceManyBody().strength(-120))
      .force("center", forceCenter(w / 2, h / 2))
      .force("collide", forceCollide<SimNode>().radius((d) => getRadius(d.id) + 2))
      .alphaDecay(0.02)
      .velocityDecay(0.3);

    // Paint function
    const paint = () => {
      const { x: tx, y: ty, k } = transformRef.current;
      ctx.save();
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#030712"; // gray-950
      ctx.fillRect(0, 0, w, h);
      ctx.translate(tx, ty);
      ctx.scale(k, k);

      // Draw edges
      for (const link of simLinks) {
        const s = link.source as SimNode;
        const t = link.target as SimNode;
        if (s.x == null || t.x == null) continue;
        const isConnected = selectedNodeId && (s.id === selectedNodeId || t.id === selectedNodeId);
        ctx.beginPath();
        ctx.moveTo(s.x, s.y!);
        ctx.lineTo(t.x, t.y!);
        ctx.strokeStyle = isConnected ? "#60a5fa66" : "#374151";
        ctx.lineWidth = isConnected ? 1.5 : 0.5;
        ctx.stroke();
      }

      // Draw nodes
      for (const node of simNodes) {
        if (node.x == null) continue;
        const radius = getRadius(node.id);
        const color = getNodeColor(node);
        const isSelected = node.id === selectedNodeId;
        const isMatch = searchTerm && node.id.toLowerCase().includes(searchTerm.toLowerCase());
        const dimmed = searchTerm && !isMatch;

        ctx.beginPath();
        ctx.arc(node.x, node.y!, radius, 0, 2 * Math.PI);
        ctx.fillStyle = dimmed ? `${color}33` : color;
        ctx.fill();

        if (isSelected) {
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // Label for high-degree, selected, or matched nodes
        const degree = degreeMap.get(node.id) ?? 1;
        if (degree >= 3 || isSelected || isMatch) {
          ctx.font = `${isSelected ? "bold " : ""}${Math.max(3, radius * 0.8)}px sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          ctx.fillStyle = dimmed ? "#9ca3af55" : "#e5e7eb";
          ctx.fillText(node.id, node.x, node.y! + radius + 2);
        }
      }

      ctx.restore();
    };

    simulation.on("tick", paint);

    // Click hit-test
    const handleClick = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const { x: tx, y: ty, k } = transformRef.current;
      const mx = (e.clientX - rect.left - tx) / k;
      const my = (e.clientY - rect.top - ty) / k;

      for (const node of simNodes) {
        if (node.x == null) continue;
        const r = getRadius(node.id) + 4; // generous hit area
        const dx = mx - node.x;
        const dy = my - node.y!;
        if (dx * dx + dy * dy < r * r) {
          onNodeClick(node);
          return;
        }
      }
    };
    canvas.addEventListener("click", handleClick);

    // Pan + zoom
    let isPanning = false;
    let panStart = { x: 0, y: 0 };

    const handleMouseDown = (e: MouseEvent) => {
      if (e.button === 0) {
        isPanning = true;
        panStart = { x: e.clientX - transformRef.current.x, y: e.clientY - transformRef.current.y };
      }
    };
    const handleMouseMove = (e: MouseEvent) => {
      if (!isPanning) return;
      transformRef.current.x = e.clientX - panStart.x;
      transformRef.current.y = e.clientY - panStart.y;
      paint();
    };
    const handleMouseUp = () => { isPanning = false; };
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const t = transformRef.current;
      const factor = e.deltaY < 0 ? 1.1 : 0.9;
      const newK = Math.min(Math.max(t.k * factor, 0.1), 10);
      t.x = mx - (mx - t.x) * (newK / t.k);
      t.y = my - (my - t.y) * (newK / t.k);
      t.k = newK;
      paint();
    };

    canvas.addEventListener("mousedown", handleMouseDown);
    canvas.addEventListener("mousemove", handleMouseMove);
    canvas.addEventListener("mouseup", handleMouseUp);
    canvas.addEventListener("mouseleave", handleMouseUp);
    canvas.addEventListener("wheel", handleWheel, { passive: false });

    // Cleanup
    return () => {
      simulation.stop();
      resizeObserver.disconnect();
      canvas.removeEventListener("click", handleClick);
      canvas.removeEventListener("mousedown", handleMouseDown);
      canvas.removeEventListener("mousemove", handleMouseMove);
      canvas.removeEventListener("mouseup", handleMouseUp);
      canvas.removeEventListener("mouseleave", handleMouseUp);
      canvas.removeEventListener("wheel", handleWheel);
    };
  }, [nodes, edges, getRadius, degreeMap]);

  // Repaint on selection/search change without restarting simulation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || simNodesRef.current.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width / devicePixelRatio;
    const h = canvas.height / devicePixelRatio;
    const simNodes = simNodesRef.current;
    const simLinks = simLinksRef.current;
    const { x: tx, y: ty, k } = transformRef.current;

    ctx.save();
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#030712";
    ctx.fillRect(0, 0, w, h);
    ctx.translate(tx, ty);
    ctx.scale(k, k);

    for (const link of simLinks) {
      const s = link.source as SimNode;
      const t = link.target as SimNode;
      if (s.x == null || t.x == null) continue;
      const isConnected = selectedNodeId && (s.id === selectedNodeId || t.id === selectedNodeId);
      ctx.beginPath();
      ctx.moveTo(s.x, s.y!);
      ctx.lineTo(t.x, t.y!);
      ctx.strokeStyle = isConnected ? "#60a5fa66" : "#374151";
      ctx.lineWidth = isConnected ? 1.5 : 0.5;
      ctx.stroke();
    }

    for (const node of simNodes) {
      if (node.x == null) continue;
      const radius = getRadius(node.id);
      const color = getNodeColor(node);
      const isSelected = node.id === selectedNodeId;
      const isMatch = searchTerm && node.id.toLowerCase().includes(searchTerm.toLowerCase());
      const dimmed = searchTerm && !isMatch;

      ctx.beginPath();
      ctx.arc(node.x, node.y!, radius, 0, 2 * Math.PI);
      ctx.fillStyle = dimmed ? `${color}33` : color;
      ctx.fill();

      if (isSelected) {
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      const degree = degreeMap.get(node.id) ?? 1;
      if (degree >= 3 || isSelected || isMatch) {
        ctx.font = `${isSelected ? "bold " : ""}${Math.max(3, radius * 0.8)}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = dimmed ? "#9ca3af55" : "#e5e7eb";
        ctx.fillText(node.id, node.x, node.y! + radius + 2);
      }
    }

    ctx.restore();
  }, [selectedNodeId, searchTerm, degreeMap, getRadius]);

  return (
    <div ref={containerRef} className="flex-1 bg-gray-950 relative" data-testid="graph-viewer">
      <canvas ref={canvasRef} className="absolute inset-0" />
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-gray-600">
          No nodes to display
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write component test**

Create `openraven-ui/tests/components/GraphViewer.test.tsx`:

```tsx
/** @jsxImportSource react */
// @bun-env happy-dom
import { describe, it, expect } from "bun:test";
import { render } from "@testing-library/react";
import "@testing-library/jest-dom";
import GraphViewer from "../../src/components/GraphViewer";

const sampleNodes = [
  { id: "KAFKA", labels: ["technology"], properties: { entity_type: "technology", description: "Streaming" } },
  { id: "EDA", labels: ["concept"], properties: { entity_type: "concept", description: "Architecture" } },
];
const sampleEdges = [
  { id: "KAFKA-EDA", type: "DIRECTED", source: "KAFKA", target: "EDA", properties: { weight: "1.0" } },
];

describe("GraphViewer", () => {
  it("renders the graph container", () => {
    const { container } = render(
      <GraphViewer nodes={sampleNodes} edges={sampleEdges} selectedNodeId={null} onNodeClick={() => {}} searchTerm="" />
    );
    const viewer = container.querySelector('[data-testid="graph-viewer"]');
    expect(viewer).not.toBeNull();
  });

  it("renders a canvas element", () => {
    const { container } = render(
      <GraphViewer nodes={sampleNodes} edges={sampleEdges} selectedNodeId={null} onNodeClick={() => {}} searchTerm="" />
    );
    const canvas = container.querySelector("canvas");
    expect(canvas).not.toBeNull();
  });

  it("renders with empty data without crashing and shows placeholder", () => {
    const { container } = render(
      <GraphViewer nodes={[]} edges={[]} selectedNodeId={null} onNodeClick={() => {}} searchTerm="" />
    );
    const viewer = container.querySelector('[data-testid="graph-viewer"]');
    expect(viewer).not.toBeNull();
    expect(viewer?.textContent).toContain("No nodes to display");
  });
});
```

- [ ] **Step 3: Run component test**

Run: `cd openraven-ui && bun test tests/components/GraphViewer.test.tsx`
Expected: 3 tests PASS

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven-ui/src/components/GraphViewer.tsx openraven-ui/tests/components/GraphViewer.test.tsx
git commit -m "feat(ui): add GraphViewer with direct d3-force + canvas rendering"
```

---

## Task 7: React — `GraphPage` with search and filter controls

**Files:**
- Create: `openraven-ui/src/pages/GraphPage.tsx`
- Create: `openraven-ui/tests/components/GraphPage.test.tsx`

- [ ] **Step 1: Create `GraphPage.tsx`**

Create `openraven-ui/src/pages/GraphPage.tsx`:

```tsx
import { useEffect, useState, useMemo, useCallback } from "react";
import GraphViewer, { type GraphNode, type GraphEdge } from "../components/GraphViewer";
import GraphNodeDetail from "../components/GraphNodeDetail";

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  is_truncated: boolean;
}

const ENTITY_TYPES = ["technology", "concept", "person", "organization", "event", "location"];

export default function GraphPage() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeTypes, setActiveTypes] = useState<Set<string>>(new Set(ENTITY_TYPES));

  useEffect(() => {
    fetch("/api/graph?max_nodes=500")
      .then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      })
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, []);

  const filteredNodes = useMemo(() => {
    if (!data) return [];
    return data.nodes.filter((n) => {
      const type = n.properties?.entity_type ?? n.labels[0] ?? "unknown";
      return activeTypes.has(type);
    });
  }, [data, activeTypes]);

  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const filteredEdges = useMemo(() => {
    if (!data) return [];
    return data.edges.filter((e) => {
      return filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target);
    });
  }, [data, filteredNodeIds]);

  // Clear selectedNode when it becomes invisible due to type filter
  useEffect(() => {
    if (selectedNode && !filteredNodeIds.has(selectedNode.id)) {
      setSelectedNode(null);
    }
  }, [filteredNodeIds, selectedNode]);

  const neighbors = useMemo(() => {
    if (!selectedNode || !data) return [];
    const id = selectedNode.id;
    const neighborIds = new Set<string>();
    for (const e of data.edges) {
      if (e.source === id) neighborIds.add(e.target);
      if (e.target === id) neighborIds.add(e.source);
    }
    return data.nodes
      .filter((n) => neighborIds.has(n.id))
      .map((n) => ({ id: n.id, labels: n.labels }));
  }, [selectedNode, data]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
  }, []);

  const handleNavigate = useCallback((nodeId: string) => {
    const node = data?.nodes.find((n) => n.id === nodeId);
    if (node) setSelectedNode(node);
  }, [data]);

  const toggleType = (type: string) => {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  if (loading) return <div className="text-gray-500 p-8" data-testid="graph-loading">Loading graph...</div>;
  if (error) return <div className="text-red-400 p-8" data-testid="graph-error">Error: {error}</div>;
  if (!data || data.nodes.length === 0) {
    return (
      <div className="text-gray-500 p-8" data-testid="graph-empty">
        <h1 className="text-2xl font-bold text-white mb-2">Knowledge Graph</h1>
        <p>No graph data yet. Add files to start building your knowledge graph.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-800 bg-gray-950">
        <input
          type="text"
          placeholder="Search nodes..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded px-3 py-1 text-sm text-gray-200 placeholder-gray-600 w-48 focus:outline-none focus:border-blue-500"
        />
        <div className="flex gap-1">
          {ENTITY_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => toggleType(type)}
              className={`text-xs px-2 py-1 rounded border ${
                activeTypes.has(type)
                  ? "border-gray-600 bg-gray-800 text-gray-200"
                  : "border-gray-800 bg-gray-950 text-gray-600"
              }`}
            >
              {type}
            </button>
          ))}
        </div>
        <span className="text-xs text-gray-600 ml-auto">
          {filteredNodes.length} nodes / {filteredEdges.length} edges
          {data.is_truncated && " (truncated)"}
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
        />
        {selectedNode && (
          <GraphNodeDetail
            node={selectedNode}
            neighbors={neighbors}
            onClose={() => setSelectedNode(null)}
            onNavigate={handleNavigate}
          />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write GraphPage tests for empty/error states**

Create `openraven-ui/tests/components/GraphPage.test.tsx`:

```tsx
/** @jsxImportSource react */
// @bun-env happy-dom
import { describe, it, expect, mock, beforeEach } from "bun:test";
import { render, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { BrowserRouter } from "react-router-dom";

// We don't need the actual canvas rendering for these tests
mock.module("d3-force", () => ({
  forceSimulation: () => ({
    force: function() { return this; },
    alphaDecay: function() { return this; },
    velocityDecay: function() { return this; },
    on: function() { return this; },
    stop: function() {},
  }),
  forceLink: () => { const f = () => f; f.id = () => f; f.distance = () => f; return f; },
  forceManyBody: () => { const f = () => f; f.strength = () => f; return f; },
  forceCenter: () => () => {},
  forceCollide: () => { const f = () => f; f.radius = () => f; return f; },
}));

const { default: GraphPage } = await import("../../src/pages/GraphPage");

function renderWithRouter(component: React.ReactElement) {
  return render(<BrowserRouter>{component}</BrowserRouter>);
}

describe("GraphPage", () => {
  beforeEach(() => {
    // Reset fetch mock before each test
    globalThis.fetch = mock(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ nodes: [], edges: [], is_truncated: false }),
      } as Response)
    );
  });

  it("shows loading state initially", () => {
    // Make fetch hang
    globalThis.fetch = mock(() => new Promise(() => {}));
    const { container } = renderWithRouter(<GraphPage />);
    const loading = container.querySelector('[data-testid="graph-loading"]');
    expect(loading).not.toBeNull();
  });

  it("shows empty state when graph has no data", async () => {
    const { container } = renderWithRouter(<GraphPage />);
    await waitFor(() => {
      const empty = container.querySelector('[data-testid="graph-empty"]');
      expect(empty).not.toBeNull();
    });
  });

  it("shows error state when API fails", async () => {
    globalThis.fetch = mock(() =>
      Promise.resolve({ ok: false, status: 500 } as Response)
    );
    const { container } = renderWithRouter(<GraphPage />);
    await waitFor(() => {
      const error = container.querySelector('[data-testid="graph-error"]');
      expect(error).not.toBeNull();
    });
  });
});
```

- [ ] **Step 3: Run GraphPage tests**

Run: `cd openraven-ui && bun test tests/components/GraphPage.test.tsx`
Expected: 3 tests PASS

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven-ui/src/pages/GraphPage.tsx openraven-ui/tests/components/GraphPage.test.tsx
git commit -m "feat(ui): add GraphPage with search, filter, and detail panel"
```

---

## Task 8: Wire up routing — App.tsx with full-width graph layout

**Files:**
- Modify: `openraven-ui/src/App.tsx`

> **Review fix applied:** Uses a single `<Routes>` tree with conditional className on a shared `<main>` wrapper. Avoids the dual-`<Routes>` pattern which causes unmount flicker. Uses flexbox `h-screen` + `flex-1` instead of hardcoded `57px`.

- [ ] **Step 1: Update App.tsx to add graph route and conditional layout**

Replace the entire content of `openraven-ui/src/App.tsx`:

```tsx
import { Routes, Route, NavLink, useLocation } from "react-router-dom";
import AskPage from "./pages/AskPage";
import StatusPage from "./pages/StatusPage";
import IngestPage from "./pages/IngestPage";
import GraphPage from "./pages/GraphPage";

export default function App() {
  const location = useLocation();
  const isGraphPage = location.pathname === "/graph";

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100">
      <nav className="border-b border-gray-800 px-6 py-3 flex items-center gap-6 shrink-0">
        <span className="text-lg font-bold text-white tracking-tight">OpenRaven</span>
        <NavLink to="/" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Ask</NavLink>
        <NavLink to="/ingest" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Add Files</NavLink>
        <NavLink to="/graph" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Graph</NavLink>
        <NavLink to="/status" className={({ isActive }) => isActive ? "text-blue-400" : "text-gray-400 hover:text-gray-200"}>Status</NavLink>
      </nav>
      <main className={isGraphPage ? "flex-1 flex flex-col min-h-0" : "max-w-4xl mx-auto px-6 py-8 w-full flex-1"}>
        <Routes>
          <Route path="/" element={<AskPage />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/status" element={<StatusPage />} />
        </Routes>
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Verify dev server loads correctly**

Run: `cd openraven-ui && bun run build`
Expected: Build succeeds. Vite output shows all chunks including GraphPage.

- [ ] **Step 3: Run all existing UI tests to confirm nothing broke**

Run: `cd openraven-ui && bun test tests/`
Expected: All existing tests still PASS + new graph tests PASS

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/source/OpenRaven
git add openraven-ui/src/App.tsx
git commit -m "feat(ui): wire up /graph route with full-width layout"
```

---

## Task 9: Restart PM2 and verify end-to-end

**Files:** None (runtime verification only)

- [ ] **Step 1: Rebuild the UI**

```bash
cd openraven-ui && bun run build
```

- [ ] **Step 2: Restart PM2 services**

```bash
pm2 restart all
```

- [ ] **Step 3: Verify backend graph endpoint**

```bash
curl -s http://localhost:8741/api/graph | python3 -m json.tool | head -20
```

Expected: JSON with `nodes`, `edges`, `is_truncated` fields. If KB is empty, nodes/edges will be empty arrays.

- [ ] **Step 4: Verify Hono proxy**

```bash
curl -s http://localhost:3002/api/graph | python3 -m json.tool | head -20
```

Expected: Same JSON response proxied through Hono.

- [ ] **Step 5: Verify UI loads the graph page**

Open `http://localhost:3002/graph` in browser. Expected:
- If KB has data: force-directed graph renders with colored nodes, clickable for detail panel
- If KB is empty: "No graph data yet" message

- [ ] **Step 6: Run full test suite**

```bash
cd /home/ubuntu/source/OpenRaven/openraven && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py
cd /home/ubuntu/source/OpenRaven/openraven-ui && bun test tests/
```

Expected: All Python tests pass (43+), all Bun tests pass (29+). Zero failures.

- [ ] **Step 7: Final commit (if any fixes were needed)**

```bash
cd /home/ubuntu/source/OpenRaven
git add -A
git commit -m "fix: resolve any issues found during E2E verification"
```

---

## Summary

| Task | What | Tests Added |
|---|---|---|
| 1 | `RavenGraph.get_graph_data()` | 4 Python unit tests |
| 2 | `GET /api/graph` FastAPI endpoint | 3 Python API tests |
| 3 | Hono proxy route + core-client | 3 Bun route tests |
| 4 | Install `d3-force` + `d3-quadtree` | Build verification |
| 5 | `GraphNodeDetail` component | — |
| 6 | `GraphViewer` (d3-force + canvas) | 3 Bun component tests |
| 7 | `GraphPage` with controls | 3 Bun page tests |
| 8 | Wire routing in App.tsx | Existing tests regression |
| 9 | PM2 restart + E2E verify | Manual + full suite |

**Total new tests: 16** (4 Python unit + 3 Python API + 3 Bun route + 3 Bun component + 3 Bun page)
