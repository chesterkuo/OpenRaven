export interface IngestResult {
  files_processed: number;
  entities_extracted: number;
  articles_generated: number;
  errors: string[];
}

export interface Settings {
  apiUrl: string;
  authMode: "local" | "cloud";
}

const DEFAULT_SETTINGS: Settings = { apiUrl: "http://localhost:3002", authMode: "local" };

export async function getSettings(): Promise<Settings> {
  return new Promise((resolve) => {
    chrome.storage.sync.get(["apiUrl", "authMode"], (data) => {
      resolve({
        apiUrl: (data.apiUrl || DEFAULT_SETTINGS.apiUrl).replace(/\/+$/, ""),
        authMode: data.authMode || DEFAULT_SETTINGS.authMode,
      });
    });
  });
}

async function getAuthHeaders(settings: Settings): Promise<Record<string, string>> {
  if (settings.authMode !== "cloud") return {};
  try {
    const cookie = await chrome.cookies.get({ url: settings.apiUrl, name: "session_id" });
    if (cookie) return { Cookie: `session_id=${cookie.value}` };
  } catch {}
  return {};
}

export async function sendToOpenRaven(
  title: string,
  url: string,
  text: string,
): Promise<IngestResult> {
  const settings = await getSettings();
  const markdown = `# ${title}\n\n> Source: ${url}\n\n${text}`;
  const filename = title.replace(/[^a-zA-Z0-9_\- ]/g, "").slice(0, 80).trim() + ".md";

  const formData = new FormData();
  formData.append("files", new Blob([markdown], { type: "text/markdown" }), filename);

  const authHeaders = await getAuthHeaders(settings);
  const response = await fetch(`${settings.apiUrl}/api/ingest`, {
    method: "POST",
    headers: authHeaders,
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`OpenRaven API error: ${response.status}`);
  }

  return response.json();
}

export async function checkConnection(): Promise<{ connected: boolean; authenticated: boolean }> {
  const settings = await getSettings();
  try {
    const res = await fetch(`${settings.apiUrl}/health`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) return { connected: false, authenticated: false };

    if (settings.authMode === "cloud") {
      const authHeaders = await getAuthHeaders(settings);
      const authRes = await fetch(`${settings.apiUrl}/api/auth/me`, {
        headers: authHeaders,
        signal: AbortSignal.timeout(3000),
      });
      return { connected: true, authenticated: authRes.ok };
    }

    return { connected: true, authenticated: true };
  } catch {
    return { connected: false, authenticated: false };
  }
}
