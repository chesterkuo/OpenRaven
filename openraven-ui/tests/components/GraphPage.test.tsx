/** @jsxImportSource react */
// @bun-env happy-dom
import { describe, it, expect, mock, beforeEach } from "bun:test";
import { render, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { BrowserRouter } from "react-router-dom";

// Mock d3-force since happy-dom doesn't have canvas
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
    globalThis.fetch = mock(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ nodes: [], edges: [], is_truncated: false }),
      } as Response)
    );
  });

  it("shows loading state initially", () => {
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
