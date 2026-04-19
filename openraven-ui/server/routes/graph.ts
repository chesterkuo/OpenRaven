import { Hono } from "hono";

const CORE_API_URL = process.env.CORE_API_URL ?? "http://127.0.0.1:8741";

const graphRouter = new Hono();

graphRouter.get("/", async (c) => {
  try {
    const maxNodes = c.req.query("max_nodes") ?? "500";
    const headers: Record<string, string> = {};
    const cookie = c.req.header("cookie");
    if (cookie) headers["cookie"] = cookie;

    const res = await fetch(`${CORE_API_URL}/api/graph?max_nodes=${maxNodes}`, { headers });
    const text = await res.text();
    try {
      return c.json(JSON.parse(text), res.status as any);
    } catch {
      return c.text(text, res.status as any);
    }
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});

graphRouter.get("/subgraph", async (c) => {
  try {
    const qs = c.req.url.includes("?") ? "?" + c.req.url.split("?")[1] : "";
    const headers: Record<string, string> = {};
    const cookie = c.req.header("cookie");
    if (cookie) headers["cookie"] = cookie;

    const res = await fetch(`${CORE_API_URL}/api/graph/subgraph${qs}`, { headers });
    const text = await res.text();
    try {
      return c.json(JSON.parse(text), res.status as any);
    } catch {
      return c.text(text, res.status as any);
    }
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});

graphRouter.get("/node/:id/context", async (c) => {
  try {
    const nodeId = c.req.param("id");
    const headers: Record<string, string> = {};
    const cookie = c.req.header("cookie");
    if (cookie) headers["cookie"] = cookie;

    const res = await fetch(`${CORE_API_URL}/api/graph/node/${encodeURIComponent(nodeId)}/context`, { headers });
    const text = await res.text();
    try {
      return c.json(JSON.parse(text), res.status as any);
    } catch {
      return c.text(text, res.status as any);
    }
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});

export default graphRouter;
