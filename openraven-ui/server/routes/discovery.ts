import { Hono } from "hono";
import { getDiscoveryInsights } from "../services/core-client";

const discoveryRouter = new Hono();

discoveryRouter.get("/", async (c) => {
  try {
    const insights = await getDiscoveryInsights();
    return c.json(insights);
  } catch {
    return c.json([]);
  }
});

export default discoveryRouter;
