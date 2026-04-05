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

// Shared proxy helper
const CORE_API_URL = process.env.CORE_API_URL ?? "http://127.0.0.1:8741";
async function proxyToCore(c: any, extraPath?: string) {
  const url = `${CORE_API_URL}${c.req.path}${c.req.url.includes("?") ? "?" + c.req.url.split("?")[1] : ""}`;
  const headers: Record<string, string> = {};
  const cookie = c.req.header("cookie");
  if (cookie) headers["cookie"] = cookie;
  const ct = c.req.header("content-type");
  if (ct) headers["content-type"] = ct;
  const body = c.req.method === "GET" || c.req.method === "HEAD" ? undefined : await c.req.text();
  const res = await fetch(url, { method: c.req.method, headers, body });
  const text = await res.text();
  try { return c.json(JSON.parse(text), res.status as any); }
  catch { return c.text(text, res.status as any); }
}

// Proxy health endpoints to core API
app.all("/api/health/*", async (c) => {
  try { return await proxyToCore(c); }
  catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
// Proxy all API endpoints using shared helper
app.all("/api/connectors/*", async (c) => {
  try { return await proxyToCore(c); }
  catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
app.all("/api/agents/*", async (c) => {
  try { return await proxyToCore(c); }
  catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
app.all("/api/agents", async (c) => {
  try { return await proxyToCore(c); }
  catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
// Course proxy with binary passthrough for zip downloads
app.all("/api/courses/*", async (c) => {
  try {
    if (c.req.path.endsWith("/download")) {
      const url = `${CORE_API_URL}${c.req.path}`;
      const res = await fetch(url, { method: c.req.method });
      return new Response(res.body, {
        status: res.status,
        headers: {
          "content-type": res.headers.get("content-type") || "application/octet-stream",
          "content-disposition": res.headers.get("content-disposition") || "",
        },
      });
    }
    return await proxyToCore(c);
  } catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
app.all("/api/courses", async (c) => {
  try { return await proxyToCore(c); }
  catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
app.all("/api/config/*", async (c) => {
  try { return await proxyToCore(c); }
  catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
app.get("/api/schemas", async (c) => {
  try { return await proxyToCore(c); }
  catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});

// Audit log proxy with binary passthrough for CSV export
app.all("/api/audit/*", async (c) => {
  try {
    if (c.req.path.endsWith("/export")) {
      const url = `${CORE_API_URL}${c.req.path}${c.req.url.includes("?") ? "?" + c.req.url.split("?")[1] : ""}`;
      const res = await fetch(url, {
        method: c.req.method,
        headers: { Cookie: c.req.header("Cookie") ?? "" },
      });
      return new Response(res.body, {
        status: res.status,
        headers: {
          "content-type": res.headers.get("content-type") || "text/csv",
          "content-disposition": res.headers.get("content-disposition") || "attachment; filename=audit_logs.csv",
        },
      });
    }
    return await proxyToCore(c);
  } catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});
app.all("/api/audit", async (c) => {
  try { return await proxyToCore(c); }
  catch (e) { return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502); }
});

// Auth passthrough (with cookie forwarding for session management)
app.all("/api/auth/*", async (c) => {
  const url = `${CORE_API_URL}${c.req.path}`;
  const headers: Record<string, string> = { "content-type": c.req.header("content-type") || "application/json" };
  const cookie = c.req.header("cookie");
  if (cookie) headers["cookie"] = cookie;

  const init: RequestInit = { method: c.req.method, headers };
  if (c.req.method === "POST") {
    init.body = await c.req.text();
  }

  const res = await fetch(url, init);
  const responseHeaders = new Headers();
  // Forward Set-Cookie headers for session management
  const setCookie = res.headers.get("set-cookie");
  if (setCookie) responseHeaders.set("set-cookie", setCookie);
  responseHeaders.set("content-type", res.headers.get("content-type") || "application/json");

  return new Response(await res.text(), {
    status: res.status,
    headers: responseHeaders,
  });
});

// Serve built frontend assets from dist/
app.use("/assets/*", serveStatic({ root: "./dist" }));

// SPA fallback: serve index.html for all non-API routes
app.get("*", serveStatic({ root: "./dist", path: "index.html" }));

const port = Number(process.env.PORT ?? 3000);
console.log(`OpenRaven UI server running on http://localhost:${port}`);

export default { port, fetch: app.fetch };
