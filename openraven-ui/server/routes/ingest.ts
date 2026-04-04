import { Hono } from "hono";
import { ingestFiles } from "../services/core-client";

const ingestRouter = new Hono();

ingestRouter.post("/", async (c) => {
  const body = await c.req.formData();
  const coreForm = new FormData();
  for (const [, value] of body.entries()) {
    if (value instanceof File) coreForm.append("files", value);
  }
  try {
    const result = await ingestFiles(coreForm);
    return c.json(result);
  } catch (e) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return c.json({ error: `Core engine error: ${message}` }, 502);
  }
});

export default ingestRouter;
