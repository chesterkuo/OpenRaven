import { Hono } from "hono";
import { getWikiList, getWikiArticle } from "../services/core-client";

const wikiRouter = new Hono();

wikiRouter.get("/", async (c) => {
  try {
    const list = await getWikiList();
    return c.json(list);
  } catch (e) {
    return c.json({ error: `Core engine error: ${(e as Error).message}` }, 502);
  }
});

wikiRouter.get("/:slug", async (c) => {
  try {
    const slug = c.req.param("slug");
    const article = await getWikiArticle(slug);
    return c.json(article);
  } catch (e) {
    const msg = (e as Error).message;
    const status = msg.includes("404") ? 404 : 502;
    return c.json({ error: msg }, status);
  }
});

export default wikiRouter;
