"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DocumentItem, deleteDocument, fetchLibrary, uploadDocument } from "@/lib/api";

export function LibraryManager() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lawName, setLawName] = useState("");
  const [versionDate, setVersionDate] = useState("");
  const [file, setFile] = useState<File | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setDocuments(await fetchLibrary());
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleUpload(event: React.FormEvent) {
    event.preventDefault();
    if (!file || !lawName.trim()) return;

    setUploading(true);
    setError(null);
    try {
      await uploadDocument(file, lawName.trim(), versionDate.trim());
      setLawName("");
      setVersionDate("");
      setFile(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(documentId: number, name: string) {
    if (!confirm(`确定从资料库移除「${name}」？`)) return;
    setError(null);
    try {
      await deleteDocument(documentId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    }
  }

  const totalChunks = documents.reduce((sum, doc) => sum + doc.chunk_count, 0);

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-4 py-8">
      <header className="mb-8 flex items-start justify-between gap-4 border-b border-zinc-200 pb-6 dark:border-zinc-800">
        <div>
          <p className="text-sm font-medium text-amber-700 dark:text-amber-400">资料库管理</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">法律资料库</h1>
          <p className="mt-3 text-sm text-zinc-600 dark:text-zinc-400">
            已收录 {documents.length} 部法律，共 {totalChunks} 个条文片段。上传后立即可用于问答检索。
          </p>
        </div>
        <Link
          href="/"
          className="rounded-xl border border-zinc-300 px-4 py-2 text-sm hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900"
        >
          返回对话
        </Link>
      </header>

      <section className="mb-10 rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="text-lg font-semibold">上传新法律</h2>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          支持 .txt / .md / .pdf / .docx。系统会按「第 X 条」自动分块入库。
        </p>
        <form onSubmit={handleUpload} className="mt-6 grid gap-4 md:grid-cols-2">
          <label className="grid gap-2 text-sm">
            法律名称 *
            <input
              value={lawName}
              onChange={(e) => setLawName(e.target.value)}
              placeholder="例如：中华人民共和国合同法"
              className="rounded-xl border border-zinc-300 bg-transparent px-3 py-2 dark:border-zinc-700"
              required
            />
          </label>
          <label className="grid gap-2 text-sm">
            版本日期
            <input
              value={versionDate}
              onChange={(e) => setVersionDate(e.target.value)}
              placeholder="例如：2023-12-29"
              className="rounded-xl border border-zinc-300 bg-transparent px-3 py-2 dark:border-zinc-700"
            />
          </label>
          <label className="grid gap-2 text-sm md:col-span-2">
            法律文件 *
            <input
              type="file"
              accept=".txt,.md,.pdf,.docx"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="rounded-xl border border-zinc-300 bg-transparent px-3 py-2 dark:border-zinc-700"
              required
            />
          </label>
          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={uploading || !file || !lawName.trim()}
              className="rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
            >
              {uploading ? "入库中..." : "上传并入库"}
            </button>
          </div>
        </form>
      </section>

      {error && (
        <p className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
          {error}
        </p>
      )}

      <section className="rounded-2xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
        <div className="border-b border-zinc-200 px-6 py-4 dark:border-zinc-800">
          <h2 className="text-lg font-semibold">已收录法律</h2>
        </div>
        {loading ? (
          <p className="px-6 py-8 text-sm text-zinc-500">加载中...</p>
        ) : documents.length === 0 ? (
          <p className="px-6 py-8 text-sm text-zinc-500">资料库为空，请上传法律文件。</p>
        ) : (
          <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
            {documents.map((doc) => (
              <li key={doc.id} className="flex items-center justify-between gap-4 px-6 py-4">
                <div>
                  <p className="font-medium">{doc.law_name}</p>
                  <p className="mt-1 text-xs text-zinc-500">
                    {doc.chunk_count} 条 · 版本 {doc.version_date || "未标注"} · {doc.source_filename}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void handleDelete(doc.id, doc.law_name)}
                  className="rounded-lg border border-red-200 px-3 py-1 text-xs text-red-700 hover:bg-red-50 dark:border-red-900 dark:text-red-300 dark:hover:bg-red-950/30"
                >
                  移除
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
