export const TYPE_COLORS: Record<string, string> = {
  technology: "#fa520f",
  concept: "#1f1f1f",
  person: "#ffa110",
  organization: "#d94800",
  event: "#dc2626",
  location: "#8b6914",
  statute: "#2563eb",
  content: "#6b7280",
  method: "#8b6914",
  data: "#a0a0a0",
  artifact: "#16a34a",
};

export const TYPE_LABELS: Record<string, string> = {
  concept: "概念",
  content: "內容",
  organization: "組織",
  person: "人物",
  method: "方法",
  data: "數據",
  event: "判決/事件",
  statute: "法條",
  artifact: "文件",
  location: "地點",
  technology: "技術",
};

export const RELATION_LABELS: Record<string, string> = {
  requirement: "要求",
  "legal basis": "依據",
  "governed by": "規範",
  "issued by": "作出",
  covers: "承保",
  component: "包含",
  "type of": "屬於",
  party: "當事人",
  "court ruling": "判決",
};

export function extractRelationLabel(keywords: string): string {
  const kw = keywords.toLowerCase();
  for (const [key, label] of Object.entries(RELATION_LABELS)) {
    if (kw.includes(key)) return label;
  }
  return "關聯";
}
