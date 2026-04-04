const CORE_API_URL = process.env.CORE_API_URL ?? "http://127.0.0.1:8741";

export interface StatusResponse {
  total_files: number;
  total_entities: number;
  total_connections: number;
  topic_count: number;
  top_topics: string[];
  confidence_avg: number;
}

export interface AskResponse {
  answer: string;
  mode: string;
}

export interface IngestResponse {
  files_processed: number;
  entities_extracted: number;
  articles_generated: number;
  errors: string[];
}

export interface DiscoveryInsight {
  insight_type: string;
  title: string;
  description: string;
  related_entities: string[];
}

export interface GraphNode {
  id: string;
  labels: string[];
  properties: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  type: string;
  source: string;
  target: string;
  properties: Record<string, any>;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  is_truncated: boolean;
}

export async function getGraphData(maxNodes: number = 500): Promise<GraphResponse> {
  const res = await fetch(`${CORE_API_URL}/api/graph?max_nodes=${maxNodes}`);
  if (!res.ok) throw new Error(`Core API error: ${res.status}`);
  return res.json();
}

export async function getStatus(): Promise<StatusResponse> {
  const res = await fetch(`${CORE_API_URL}/api/status`);
  if (!res.ok) throw new Error(`Core API error: ${res.status}`);
  return res.json();
}

export async function askQuestion(question: string, mode: string = "mix"): Promise<AskResponse> {
  const res = await fetch(`${CORE_API_URL}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, mode }),
  });
  if (!res.ok) throw new Error(`Core API error: ${res.status}`);
  return res.json();
}

export async function ingestFiles(formData: FormData): Promise<IngestResponse> {
  const res = await fetch(`${CORE_API_URL}/api/ingest`, { method: "POST", body: formData });
  if (!res.ok) throw new Error(`Core API error: ${res.status}`);
  return res.json();
}

export interface WikiListItem {
  slug: string;
  title: string;
}

export interface WikiArticle {
  slug: string;
  title: string;
  content: string;
}

export async function getWikiList(): Promise<WikiListItem[]> {
  const res = await fetch(`${CORE_API_URL}/api/wiki`);
  if (!res.ok) throw new Error(`Core API error: ${res.status}`);
  return res.json();
}

export async function getWikiArticle(slug: string): Promise<WikiArticle> {
  const res = await fetch(`${CORE_API_URL}/api/wiki/${encodeURIComponent(slug)}`);
  if (!res.ok) throw new Error(`Core API error: ${res.status}`);
  return res.json();
}

export async function getDiscoveryInsights(): Promise<DiscoveryInsight[]> {
  const res = await fetch(`${CORE_API_URL}/api/discovery`);
  if (!res.ok) throw new Error(`Core API error: ${res.status}`);
  return res.json();
}
