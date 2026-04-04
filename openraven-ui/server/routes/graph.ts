import { Hono } from "hono";
import { getGraphData } from "../services/core-client";

const graphRouter = new Hono();

graphRouter.get("/", async (c) => {
  try {
    const maxNodes = Number(c.req.query("max_nodes") ?? "500");
    const data = await getGraphData(maxNodes);
    return c.json(data);
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});

export default graphRouter;
