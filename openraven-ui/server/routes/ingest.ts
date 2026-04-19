import { Hono } from "hono";
import { ingestFiles } from "../services/core-client";

const ingestRouter = new Hono();

ingestRouter.post("/", async (c) => {
  const body = await c.req.formData();
  const coreForm = new FormData();
  for (const [key, value] of body.entries()) {
    if (value instanceof File) {
      coreForm.append("files", value);
    } else if (key === "schema") {
      coreForm.append("schema", value);
    }
  }
  try {
    const cookie = c.req.header("cookie");
    const result = await ingestFiles(coreForm, cookie);
    return c.json(result);
  } catch (e) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return c.json({ error: `Core engine error: ${message}` }, 502);
  }
});

export default ingestRouter;
