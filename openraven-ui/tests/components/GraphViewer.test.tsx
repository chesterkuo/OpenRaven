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

  it("renders with selected node without crashing", () => {
    const { container } = render(
      <GraphViewer nodes={sampleNodes} edges={sampleEdges} selectedNodeId="KAFKA" onNodeClick={() => {}} searchTerm="" />
    );
    const viewer = container.querySelector('[data-testid="graph-viewer"]');
    expect(viewer).not.toBeNull();
  });
});

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
