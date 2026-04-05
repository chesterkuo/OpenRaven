import { Hono } from "hono";

const CORE_API_URL = process.env.CORE_API_URL ?? "http://127.0.0.1:8741";

const wikiRouter = new Hono();

function cookieHeaders(c: any): Record<string, string> {
  const headers: Record<string, string> = {};
  const cookie = c.req.header("cookie");
  if (cookie) headers["cookie"] = cookie;
  return headers;
}

wikiRouter.get("/", async (c) => {
  try {
    const res = await fetch(`${CORE_API_URL}/api/wiki`, { headers: cookieHeaders(c) });
    const text = await res.text();
    try { return c.json(JSON.parse(text), res.status as any); }
    catch { return c.text(text, res.status as any); }
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});

wikiRouter.get("/:slug", async (c) => {
  try {
    const slug = c.req.param("slug");
    const res = await fetch(`${CORE_API_URL}/api/wiki/${encodeURIComponent(slug)}`, { headers: cookieHeaders(c) });
    const text = await res.text();
    const status = res.status as any;
    try { return c.json(JSON.parse(text), status); }
    catch { return c.text(text, status); }
  } catch (e) {
    const msg = (e as Error).message;
    const status = msg.includes("404") ? 404 : 502;
    return c.json({ error: msg }, status);
  }
});

export default wikiRouter;
