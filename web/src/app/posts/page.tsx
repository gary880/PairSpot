"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getFeed, likePost, unlikePost } from "@/lib/api";
import type { Post } from "@/lib/types";

const LIMIT = 20;

export default function FeedPage() {
  const router = useRouter();
  const [posts, setPosts] = useState<Post[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadFeed(0, true);
  // loadFeed is stable - defined inside component but doesn't need to be in deps
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadFeed(nextOffset: number, replace: boolean) {
    if (replace) setLoading(true);
    else setLoadingMore(true);
    setError("");
    try {
      const res = await getFeed(nextOffset, LIMIT);
      setPosts((prev) => (replace ? res.items : [...prev, ...res.items]));
      setTotal(res.total);
      setOffset(nextOffset + res.items.length);
    } catch (err) {
      setError(err instanceof Error ? err.message : "載入失敗");
    } finally {
      if (replace) setLoading(false);
      else setLoadingMore(false);
    }
  }

  async function handleLike(post: Post) {
    try {
      const res = post.liked_by_me
        ? await unlikePost(post.id)
        : await likePost(post.id);
      setPosts((prev) =>
        prev.map((p) =>
          p.id === post.id
            ? { ...p, liked_by_me: res.liked, like_count: res.like_count }
            : p
        )
      );
    } catch {
      // ignore
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-rose-300 border-t-rose-600" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Feed</h1>
        <button
          className="btn-primary text-xs"
          onClick={() => router.push("/posts/create")}
        >
          + 發文
        </button>
      </div>

      {error && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">
          {error} —{" "}
          <button className="underline" onClick={() => loadFeed(0, true)}>
            重試
          </button>
        </p>
      )}

      {posts.length === 0 && !error && (
        <p className="py-12 text-center text-sm text-gray-400">
          還沒有貼文。成為第一個發文的情侶！
        </p>
      )}

      {posts.map((post) => (
        <PostCard key={post.id} post={post} onLike={handleLike} />
      ))}

      {posts.length < total && (
        <button
          className="btn-secondary w-full"
          disabled={loadingMore}
          onClick={() => loadFeed(offset, false)}
        >
          {loadingMore ? "載入中…" : `載入更多（${total - posts.length} 則）`}
        </button>
      )}
    </div>
  );
}

function PostCard({
  post,
  onLike,
}: {
  post: Post;
  onLike: (p: Post) => void;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      {/* Header */}
      <div className="mb-2 flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-rose-100 text-sm font-semibold text-rose-600">
          {post.author.display_name[0]?.toUpperCase() ?? "?"}
        </div>
        <div>
          <p className="text-sm font-medium">{post.author.display_name}</p>
          <p className="text-xs text-gray-400">
            {post.author.role === "partner_a" ? "Partner A" : "Partner B"} ·{" "}
            {new Date(post.created_at).toLocaleString("zh-TW", {
              month: "numeric",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
            {post.is_promoted && (
              <span className="ml-1 rounded bg-amber-100 px-1 text-amber-700">
                推廣
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Images */}
      {post.images.length > 0 && (
        <div
          className={`mb-3 grid gap-1 ${
            post.images.length === 1 ? "grid-cols-1" : "grid-cols-2"
          }`}
        >
          {post.images.slice(0, 4).map((img) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={img.id}
              src={img.thumbnail_url ?? img.image_url}
              alt=""
              className="w-full rounded object-cover"
              style={{ maxHeight: 200 }}
            />
          ))}
        </div>
      )}

      {/* Content */}
      {post.content && (
        <p className="mb-3 text-sm leading-relaxed">{post.content}</p>
      )}

      {/* Footer */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => onLike(post)}
          className={`flex items-center gap-1 text-sm ${
            post.liked_by_me ? "font-semibold text-rose-500" : "text-gray-400"
          }`}
        >
          {post.liked_by_me ? "♥" : "♡"} {post.like_count}
        </button>
        <span className="text-xs text-gray-300">
          {post.visibility === "private" ? "🔒 私密" : "🌐 公開"}
        </span>
      </div>
    </div>
  );
}
