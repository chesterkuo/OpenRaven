import { Hono } from "hono";
import { cors } from "hono/cors";
import { logger } from "hono/logger";
import { serveStatic } from "hono/bun";
import askRouter from "./routes/ask";
import ingestRouter from "./routes/ingest";
import statusRouter from "./routes/status";
import discoveryRouter from "./routes/discovery";
import graphRouter from "./routes/graph";
import wikiRouter from "./routes/wiki";

const app = new Hono();

app.use("*", logger());
app.use("*", cors({ origin: ["http://localhost:5173"] }));

app.get("/health", (c) => c.json({ status: "ok", version: "0.1.0" }));

app.route("/api/ask", askRouter);
app.route("/api/ingest", ingestRouter);
app.route("/api/status", statusRouter);
app.route("/api/discovery", discoveryRouter);
app.route("/api/graph", graphRouter);
app.route("/api/wiki", wikiRouter);

// Proxy health endpoints to core API
const CORE_API_URL = process.env.CORE_API_URL ?? "http://127.0.0.1:8741";
app.all("/api/health/*", async (c) => {
  try {
    const url = `${CORE_API_URL}${c.req.path}`;
    const res = await fetch(url, { method: c.req.method });
    const data = await res.json();
    return c.json(data, res.status as any);
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});
// Proxy connector endpoints to core API
app.all("/api/connectors/*", async (c) => {
  try {
    const url = `${CORE_API_URL}${c.req.path}${c.req.url.includes("?") ? "?" + c.req.url.split("?")[1] : ""}`;
    const headers: Record<string, string> = {};
    const ct = c.req.header("content-type");
    if (ct) headers["content-type"] = ct;
    const body = c.req.method === "GET" || c.req.method === "HEAD" ? undefined : await c.req.text();
    const res = await fetch(url, { method: c.req.method, headers, body });
    const data = await res.json();
    return c.json(data, res.status as any);
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});
// Proxy config endpoint to core API
app.get("/api/config/:path", async (c) => {
  try {
    const res = await fetch(`${CORE_API_URL}${c.req.path}`);
    return c.json(await res.json(), res.status as any);
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});

// Serve built frontend assets from dist/
app.use("/assets/*", serveStatic({ root: "./dist" }));

// SPA fallback: serve index.html for all non-API routes
app.get("*", serveStatic({ root: "./dist", path: "index.html" }));

const port = Number(process.env.PORT ?? 3000);
console.log(`OpenRaven UI server running on http://localhost:${port}`);

export default { port, fetch: app.fetch };
