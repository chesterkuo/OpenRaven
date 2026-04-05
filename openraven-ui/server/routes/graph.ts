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

export default graphRouter;
