"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  Citation,
  ChatMeta,
  DocumentItem,
  fetchCitation,
  fetchLibrary,
  streamChat,
} from "@/lib/api";

type Message = {
  role: "user" | "assistant";
  content: string;
  meta?: ChatMeta;
};

export function ChatPanel() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [library, setLibrary] = useState<DocumentItem[]>([]);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [citationDetail, setCitationDetail] = useState<string>("");
  const [conversationId, setConversationId] = useState<number | null>(null);

  useEffect(() => {
    fetchLibrary()
      .then(setLibrary)
      .catch(() => setLibrary([]));
  }, []);

  const totalChunks = useMemo(
    () => library.reduce((sum, item) => sum + item.chunk_count, 0),
    [library],
  );

  async function openCitation(citation: Citation) {
    setActiveCitation(citation);
    try {
      const detail = await fetchCitation(citation.chunk_id);
      setCitationDetail(detail.content);
    } catch {
      setCitationDetail(citation.excerpt);
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setError(null);
    setLoading(true);
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);

    let assistantContent = "";
    let assistantMeta: ChatMeta | undefined;

    try {
      for await (const eventData of streamChat(question, conversationId)) {
        if (eventData.type === "meta") {
          assistantMeta = eventData;
          if (eventData.conversation_id) {
            setConversationId(eventData.conversation_id);
          }
        } else if (eventData.type === "token") {
          assistantContent += eventData.content;
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") {
              next[next.length - 1] = {
                role: "assistant",
                content: assistantContent,
                meta: assistantMeta,
              };
            } else {
              next.push({
                role: "assistant",
                content: assistantContent,
                meta: assistantMeta,
              });
            }
            return next;
          });
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "请求失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-4 py-8">
      <header className="mb-8 border-b border-zinc-200 pb-6 dark:border-zinc-800">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
              法律资料库可信问答
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">
              引用或拒答 — 只从资料库作答
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-600 dark:text-zinc-400">
              当前资料库已收录 {library.length} 部法律，共 {totalChunks} 个条文片段。
              系统仅基于检索到的原文回答，查不到足够依据时会拒答并展示最接近条文。
            </p>
          </div>
          <Link
            href="/library"
            className="shrink-0 rounded-xl border border-zinc-300 px-4 py-2 text-sm hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900"
          >
            资料库管理
          </Link>
        </div>
      </header>

      <section className="flex-1 space-y-6">
        {messages.length === 0 && (
          <div className="rounded-2xl border border-dashed border-zinc-300 bg-zinc-50 p-8 text-sm text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900/40 dark:text-zinc-400">
            示例问题：
            <ul className="mt-3 list-disc space-y-2 pl-5">
              <li>公司股东偷偷转账是否可能违法？</li>
              <li>故意伤害他人身体一般如何处罚？</li>
              <li>建立劳动关系是否需要订立劳动合同？</li>
            </ul>
          </div>
        )}

        {messages.map((message, index) => (
          <article
            key={`${message.role}-${index}`}
            className={`rounded-2xl p-5 ${
              message.role === "user"
                ? "ml-12 bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : "mr-12 border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950"
            }`}
          >
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide opacity-70">
              {message.role === "user" ? "你的问题" : "助手回答"}
            </p>
            <div className="whitespace-pre-wrap text-sm leading-7">{message.content}</div>

            {message.meta && message.role === "assistant" && (
              <div className="mt-5 space-y-3 border-t border-zinc-200 pt-4 dark:border-zinc-800">
                {message.meta.referenced_laws.length > 0 && (
                  <p className="text-xs text-zinc-500">
                    本次引用：{message.meta.referenced_laws.join(" · ")}
                  </p>
                )}

                {message.meta.response_type !== "answer" && (
                  <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
                    {message.meta.response_type === "soft_refusal"
                      ? "软拒答：未找到足够依据，以下条文仅供参考。"
                      : message.meta.response_type === "extractive"
                        ? "摘录模式：以下内容为资料库原文摘录，未经 AI 改写。"
                        : "拒答：资料库中暂无足够法律依据。"}
                  </p>
                )}

                {message.meta.citations.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {message.meta.citations.map((citation) => (
                      <button
                        key={citation.chunk_id}
                        type="button"
                        onClick={() => openCitation(citation)}
                        className="rounded-full border border-zinc-300 px-3 py-1 text-xs hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900"
                      >
                        《{citation.law}》{citation.article || "相关条文"}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </article>
        ))}

        {error && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
            {error}
          </p>
        )}
      </section>

      <form onSubmit={handleSubmit} className="sticky bottom-0 mt-8 bg-[var(--background)] pt-4">
        <div className="rounded-2xl border border-zinc-300 bg-white p-3 shadow-sm dark:border-zinc-700 dark:bg-zinc-950">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            rows={3}
            placeholder="输入法律问题，例如：股东未经程序将公司资金转出是否违法？"
            className="w-full resize-none bg-transparent px-2 py-2 text-sm outline-none"
          />
          <div className="flex items-center justify-between px-2 pb-1">
            <p className="text-xs text-zinc-500">
              AI 生成内容仅供参考，不构成法律意见。
            </p>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
            >
              {loading ? "检索中..." : "发送"}
            </button>
          </div>
        </div>
      </form>

      {activeCitation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[80vh] w-full max-w-2xl overflow-auto rounded-2xl bg-white p-6 dark:bg-zinc-950">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">
                  《{activeCitation.law}》{activeCitation.article}
                </h2>
                {activeCitation.version_date && (
                  <p className="mt-1 text-xs text-zinc-500">
                    版本日期：{activeCitation.version_date}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => setActiveCitation(null)}
                className="rounded-lg px-3 py-1 text-sm text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-900"
              >
                关闭
              </button>
            </div>
            <pre className="whitespace-pre-wrap text-sm leading-7 text-zinc-700 dark:text-zinc-300">
              {citationDetail}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
