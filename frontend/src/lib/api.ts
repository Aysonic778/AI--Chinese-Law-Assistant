// Cloud Agent 预览通常只转发 3000 端口，API 走 Next.js 同源代理（见 next.config.ts rewrites）
export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export type Citation = {
  law: string;
  article: string;
  chunk_id: string;
  excerpt: string;
  version_date?: string;
};

export type ChatMeta = {
  type: "meta";
  response_type: "answer" | "refusal" | "soft_refusal" | "extractive";
  referenced_laws: string[];
  citations: Citation[];
  grounding_score: number;
  refusal_reason?: string | null;
  conversation_id?: number | null;
};

export type DocumentItem = {
  id: number;
  law_name: string;
  version_date: string;
  source_filename: string;
  chunk_count: number;
};

export type ChunkDetail = {
  law_name: string;
  article_number: string;
  chapter: string;
  content: string;
  version_date: string;
};

export async function fetchLibrary(): Promise<DocumentItem[]> {
  const response = await fetch(`${API_BASE}/api/library`);
  if (!response.ok) {
    throw new Error("无法加载资料库");
  }
  return response.json();
}

export async function uploadDocument(
  file: File,
  lawName: string,
  versionDate: string,
): Promise<DocumentItem> {
  const form = new FormData();
  form.append("file", file);
  form.append("law_name", lawName);
  form.append("version_date", versionDate);

  const response = await fetch(`${API_BASE}/api/library/documents`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "上传失败");
  }
  return response.json();
}

export async function deleteDocument(documentId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/api/library/documents/${documentId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error("删除失败");
  }
}

export async function fetchCitation(chunkId: string): Promise<ChunkDetail> {
  const response = await fetch(`${API_BASE}/api/library/citations/${chunkId}`);
  if (!response.ok) {
    throw new Error("无法加载引用原文");
  }
  return response.json();
}

export async function* streamChat(
  question: string,
  conversationId?: number | null,
): AsyncGenerator<
  | ChatMeta
  | { type: "token"; content: string }
  | { type: "done" }
> {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      conversation_id: conversationId ?? null,
    }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "问答请求失败");
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("无法读取流式响应");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data: ")) continue;
      const payload = JSON.parse(line.slice(6));
      yield payload;
    }
  }
}
