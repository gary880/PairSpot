"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { registerComplete } from "@/lib/api";

function CompleteContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [coupleId, setCoupleId] = useState("");
  const [emails, setEmails] = useState({ a: "", b: "" });
  const [form, setForm] = useState({
    display_name_a: "",
    display_name_b: "",
    password_a: "",
    password_b: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const paramId = searchParams.get("couple_id");
    const storedId = localStorage.getItem("pairspot_couple_id") ?? "";
    setCoupleId(paramId ?? storedId);
    setEmails({
      a: localStorage.getItem("pairspot_email_a") ?? "",
      b: localStorage.getItem("pairspot_email_b") ?? "",
    });
  }, [searchParams]);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await registerComplete({
        couple_id: coupleId,
        display_name_a: form.display_name_a,
        display_name_b: form.display_name_b,
        password_a: form.password_a,
        password_b: form.password_b,
      });
      localStorage.removeItem("pairspot_couple_id");
      localStorage.removeItem("pairspot_email_a");
      localStorage.removeItem("pairspot_email_b");
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知錯誤");
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="space-y-4 text-center">
        <div className="text-4xl">🎉</div>
        <h2 className="text-xl font-semibold text-green-700">帳號設定完成！</h2>
        <p className="text-sm text-gray-500">兩位 Partner 可以用各自的 Email 登入了。</p>
        <button
          className="btn-primary"
          onClick={() => router.push("/login")}
        >
          前往登入
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-rose-600">PairSpot</h1>
        <p className="mt-1 text-sm text-gray-500">Step 3 — 設定顯示名稱與密碼</p>
      </div>

      {coupleId && (
        <p className="text-xs text-gray-400">couple_id: {coupleId}</p>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <fieldset className="space-y-3 rounded-md border border-gray-200 p-4">
          <legend className="px-1 text-sm font-semibold text-gray-700">
            Partner A{emails.a && <span className="ml-1 font-normal text-gray-400">({emails.a})</span>}
          </legend>
          <div>
            <label className="mb-1 block text-sm font-medium">顯示名稱</label>
            <input
              className="input"
              type="text"
              name="display_name_a"
              value={form.display_name_a}
              onChange={handleChange}
              required
              placeholder="e.g. Dylan"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">密碼（至少 8 位）</label>
            <input
              className="input"
              type="password"
              name="password_a"
              value={form.password_a}
              onChange={handleChange}
              required
              minLength={8}
              placeholder="••••••••"
            />
          </div>
        </fieldset>

        <fieldset className="space-y-3 rounded-md border border-gray-200 p-4">
          <legend className="px-1 text-sm font-semibold text-gray-700">
            Partner B{emails.b && <span className="ml-1 font-normal text-gray-400">({emails.b})</span>}
          </legend>
          <div>
            <label className="mb-1 block text-sm font-medium">顯示名稱</label>
            <input
              className="input"
              type="text"
              name="display_name_b"
              value={form.display_name_b}
              onChange={handleChange}
              required
              placeholder="e.g. Alex"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">密碼（至少 8 位）</label>
            <input
              className="input"
              type="password"
              name="password_b"
              value={form.password_b}
              onChange={handleChange}
              required
              minLength={8}
              placeholder="••••••••"
            />
          </div>
        </fieldset>

        {error && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading || !coupleId}
          className="btn-primary w-full"
        >
          {loading ? "設定中…" : "完成設定"}
        </button>
      </form>
    </div>
  );
}

export default function CompleteRegistrationPage() {
  return (
    <Suspense fallback={<p className="text-sm text-gray-400">載入中…</p>}>
      <CompleteContent />
    </Suspense>
  );
}
