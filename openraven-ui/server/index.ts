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

// Serve built frontend assets from dist/
app.use("/assets/*", serveStatic({ root: "./dist" }));

// SPA fallback: serve index.html for all non-API routes
app.get("*", serveStatic({ root: "./dist", path: "index.html" }));

const port = Number(process.env.PORT ?? 3000);
console.log(`OpenRaven UI server running on http://localhost:${port}`);

export default { port, fetch: app.fetch };
