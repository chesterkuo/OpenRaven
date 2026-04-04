const OPENRAVEN_URL = "http://localhost:3002";

export interface IngestResult {
  files_processed: number;
  entities_extracted: number;
  articles_generated: number;
  errors: string[];
}

export async function sendToOpenRaven(
  title: string,
  url: string,
  text: string,
): Promise<IngestResult> {
  const markdown = `# ${title}\n\n> Source: ${url}\n\n${text}`;
  const filename = title.replace(/[^a-zA-Z0-9_\- ]/g, "").slice(0, 80).trim() + ".md";

  const formData = new FormData();
  formData.append("files", new Blob([markdown], { type: "text/markdown" }), filename);

  const response = await fetch(`${OPENRAVEN_URL}/api/ingest`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`OpenRaven API error: ${response.status}`);
  }

  return response.json();
}

export async function checkConnection(): Promise<boolean> {
  try {
    const response = await fetch(`${OPENRAVEN_URL}/health`, { signal: AbortSignal.timeout(3000) });
    return response.ok;
  } catch {
    return false;
  }
}
