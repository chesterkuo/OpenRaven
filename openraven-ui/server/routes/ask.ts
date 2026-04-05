import { Hono } from "hono";

const CORE_API_URL = process.env.CORE_API_URL ?? "http://127.0.0.1:8741";

const askRouter = new Hono();

askRouter.post("/", async (c) => {
  const headers: Record<string, string> = {
    "content-type": c.req.header("content-type") || "application/json",
  };
  const cookie = c.req.header("cookie");
  if (cookie) headers["cookie"] = cookie;

  const res = await fetch(`${CORE_API_URL}/api/ask`, {
    method: "POST",
    headers,
    body: await c.req.text(),
  });

  const text = await res.text();
  try {
    return c.json(JSON.parse(text), res.status as any);
  } catch {
    return c.text(text, res.status as any);
  }
});

export default askRouter;
