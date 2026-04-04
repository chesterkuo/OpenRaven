import { Hono } from "hono";
import { getStatus } from "../services/core-client";

const statusRouter = new Hono();

statusRouter.get("/", async (c) => {
  try {
    const status = await getStatus();
    return c.json(status);
  } catch (e) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return c.json({ error: `Core engine error: ${message}` }, 502);
  }
});

export default statusRouter;
