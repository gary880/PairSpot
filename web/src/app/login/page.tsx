"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import type { LoginResponse } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<LoginResponse | null>(null);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const res = await login(form);
      localStorage.setItem("pairspot_access_token", res.access_token);
      localStorage.setItem("pairspot_refresh_token", res.refresh_token);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知錯誤");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-rose-600">PairSpot</h1>
        <p className="mt-1 text-sm text-gray-500">登入</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium">Email</label>
          <input
            className="input"
            type="email"
            name="email"
            value={form.email}
            onChange={handleChange}
            required
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">密碼</label>
          <input
            className="input"
            type="password"
            name="password"
            value={form.password}
            onChange={handleChange}
            required
            placeholder="••••••••"
          />
        </div>

        {error && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full"
        >
          {loading ? "登入中…" : "登入"}
        </button>
      </form>

      {result && (
        <div className="space-y-2 rounded-md bg-green-50 p-4">
          <p className="text-sm font-semibold text-green-800">登入成功！</p>
          <div className="space-y-1 text-xs text-gray-600">
            <p className="font-medium text-gray-700">Access Token:</p>
            <pre className="break-all whitespace-pre-wrap rounded bg-white p-2 text-xs">
              {result.access_token}
            </pre>
            <p className="mt-2 font-medium text-gray-700">Refresh Token:</p>
            <pre className="break-all whitespace-pre-wrap rounded bg-white p-2 text-xs">
              {result.refresh_token}
            </pre>
          </div>
        </div>
      )}

      {result && (
        <button
          className="btn-primary w-full"
          onClick={() => router.push("/posts")}
        >
          前往 Feed
        </button>
      )}

      <p className="text-center text-sm text-gray-400">
        還沒有帳號？{" "}
        <button
          className="text-rose-500 underline"
          onClick={() => router.push("/register")}
        >
          前往註冊
        </button>
      </p>
    </div>
  );
}
