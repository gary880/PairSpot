"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createPost } from "@/lib/api";

export default function CreatePostPage() {
  const router = useRouter();
  const [content, setContent] = useState("");
  const [visibility, setVisibility] = useState<"public" | "private">("public");
  const [files, setFiles] = useState<FileList | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const fd = new FormData();
      if (content) fd.append("content", content);
      fd.append("visibility", visibility);
      if (files) {
        Array.from(files).forEach((f) => fd.append("images", f));
      }
      await createPost(fd);
      router.push("/posts");
    } catch (err) {
      setError(err instanceof Error ? err.message : "發文失敗");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">建立貼文</h1>
        <p className="mt-1 text-sm text-gray-400">需先登入才能發文</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium">內容（選填）</label>
          <textarea
            className="input min-h-[120px] resize-y"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="寫下你們的故事…"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">圖片（選填）</label>
          <input
            className="input"
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => setFiles(e.target.files)}
          />
          {files && files.length > 0 && (
            <p className="mt-1 text-xs text-gray-400">
              已選 {files.length} 張圖片
            </p>
          )}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">能見度</label>
          <select
            className="input"
            value={visibility}
            onChange={(e) =>
              setVisibility(e.target.value as "public" | "private")
            }
          >
            <option value="public">🌐 公開</option>
            <option value="private">🔒 私密（只有本情侶可見）</option>
          </select>
        </div>

        {error && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">
            {error}
          </p>
        )}

        <div className="flex gap-3">
          <button
            type="button"
            className="btn-secondary flex-1"
            onClick={() => router.back()}
          >
            取消
          </button>
          <button
            type="submit"
            disabled={loading || (!content && !files?.length)}
            className="btn-primary flex-1"
          >
            {loading ? "發文中…" : "發文"}
          </button>
        </div>
      </form>
    </div>
  );
}
