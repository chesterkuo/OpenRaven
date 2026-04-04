import { Hono } from "hono";
import { askQuestion } from "../services/core-client";

const askRouter = new Hono();

askRouter.post("/", async (c) => {
  const { question, mode } = await c.req.json<{ question: string; mode?: string }>();
  if (!question) return c.json({ error: "question is required" }, 400);
  try {
    const result = await askQuestion(question, mode ?? "mix");
    return c.json(result);
  } catch (e) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return c.json({ error: `Core engine error: ${message}` }, 502);
  }
});

export default askRouter;
