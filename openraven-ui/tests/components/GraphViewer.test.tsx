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
