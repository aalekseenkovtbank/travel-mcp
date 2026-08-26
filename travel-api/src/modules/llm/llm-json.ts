export function parseLlmJson(content: string): unknown {
  const trimmed = content.trim();
  const fenced = /^```(?:json)?\s*\n([\s\S]*?)\n```$/iu.exec(trimmed);
  return JSON.parse(fenced?.[1]?.trim() ?? trimmed);
}
