import { describe, it, expect, mock, beforeAll } from "bun:test";

// Mock the core-client module before importing the app so route handlers use mocked functions
const mockAskQuestion = mock(async (_question: string, _mode: string) => ({
  answer: "Test answer",
  mode: "mix",
}));

const mockGetStatus = mock(async () => ({
  total_files: 10,
  total_entities: 50,
  total_connections: 20,
  topic_count: 5,
  top_topics: ["topic1", "topic2"],
  confidence_avg: 0.85,
}));

const mockGetDiscoveryInsights = mock(async () => [
  {
    insight_type: "cluster",
    title: "Test Insight",
    description: "A test discovery insight",
    related_entities: ["entity1"],
  },
]);

const mockIngestFiles = mock(async (_formData: FormData) => ({
  files_processed: 1,
  entities_extracted: 5,
  articles_generated: 2,
  errors: [],
}));

mock.module("../../server/services/core-client", () => ({
  askQuestion: mockAskQuestion,
  getStatus: mockGetStatus,
  getDiscoveryInsights: mockGetDiscoveryInsights,
  ingestFiles: mockIngestFiles,
}));

// Import app after mocking
const { default: server } = await import("../../server/index");
const appFetch = server.fetch;

describe("GET /health", () => {
  it("returns status ok and version 0.1.0", async () => {
    const req = new Request("http://localhost/health");
    const res = await appFetch(req);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ status: "ok", version: "0.1.0" });
  });
});

describe("POST /api/ask", () => {
  it("returns 400 when body is empty object (no question)", async () => {
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const res = await appFetch(req);
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body).toMatchObject({ error: "question is required" });
  });

  it("returns 200 with answer when question is provided", async () => {
    mockAskQuestion.mockResolvedValueOnce({ answer: "Test answer", mode: "mix" });
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: "What is OpenRaven?" }),
    });
    const res = await appFetch(req);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toMatchObject({ answer: "Test answer", mode: "mix" });
  });

  it("returns 502 when core engine throws", async () => {
    mockAskQuestion.mockRejectedValueOnce(new Error("Core API error: 503"));
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: "Will this fail?" }),
    });
    const res = await appFetch(req);
    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body).toMatchObject({ error: expect.stringContaining("Core engine error") });
  });
});

describe("GET /api/status", () => {
  it("returns structured status response from core", async () => {
    mockGetStatus.mockResolvedValueOnce({
      total_files: 10,
      total_entities: 50,
      total_connections: 20,
      topic_count: 5,
      top_topics: ["topic1", "topic2"],
      confidence_avg: 0.85,
    });
    const req = new Request("http://localhost/api/status");
    const res = await appFetch(req);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toMatchObject({
      total_files: 10,
      total_entities: 50,
      total_connections: 20,
      topic_count: 5,
      confidence_avg: 0.85,
    });
    expect(Array.isArray(body.top_topics)).toBe(true);
  });

  it("returns 502 when core engine throws", async () => {
    mockGetStatus.mockRejectedValueOnce(new Error("Core API error: 500"));
    const req = new Request("http://localhost/api/status");
    const res = await appFetch(req);
    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body).toMatchObject({ error: expect.stringContaining("Core engine error") });
  });
});

describe("GET /api/discovery", () => {
  it("returns array of discovery insights", async () => {
    mockGetDiscoveryInsights.mockResolvedValueOnce([
      {
        insight_type: "cluster",
        title: "Test Insight",
        description: "A test discovery insight",
        related_entities: ["entity1"],
      },
    ]);
    const req = new Request("http://localhost/api/discovery");
    const res = await appFetch(req);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
    expect(body.length).toBeGreaterThan(0);
    expect(body[0]).toMatchObject({ insight_type: "cluster", title: "Test Insight" });
  });

  it("returns empty array when core engine throws", async () => {
    mockGetDiscoveryInsights.mockRejectedValueOnce(new Error("Core API error: 500"));
    const req = new Request("http://localhost/api/discovery");
    const res = await appFetch(req);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
    expect(body.length).toBe(0);
  });
});
