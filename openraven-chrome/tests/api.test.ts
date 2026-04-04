import { describe, it, expect, mock, beforeEach } from "bun:test";

describe("api", () => {
  beforeEach(() => {
    globalThis.fetch = mock(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ files_processed: 1, entities_extracted: 3, articles_generated: 1, errors: [] }),
      } as Response)
    );
  });

  it("checkConnection returns true when server is up", async () => {
    const { checkConnection } = await import("../src/api");
    const result = await checkConnection();
    expect(result).toBe(true);
  });

  it("checkConnection returns false when server is down", async () => {
    globalThis.fetch = mock(() => Promise.reject(new Error("ECONNREFUSED")));
    const { checkConnection } = await import("../src/api");
    const result = await checkConnection();
    expect(result).toBe(false);
  });
});
