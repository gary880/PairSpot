"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { registerInitiate } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    email_a: "",
    email_b: "",
    couple_name: "",
    anniversary_date: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      const payload = {
        email_a: form.email_a,
        email_b: form.email_b,
        couple_name: form.couple_name,
        ...(form.anniversary_date ? { anniversary_date: form.anniversary_date } : {}),
      };
      const res = await registerInitiate(payload);
      localStorage.setItem("pairspot_couple_id", res.couple_id);
      localStorage.setItem("pairspot_email_a", form.email_a);
      localStorage.setItem("pairspot_email_b", form.email_b);
      setSuccess(
        `成功！couple_id: ${res.couple_id}\n${res.message}\n\n請檢查雙方 Email 收件匣，點擊驗證連結。`
      );
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
        <p className="mt-1 text-sm text-gray-500">Step 1 — 建立帳號</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium">
            Partner A — Email
          </label>
          <input
            className="input"
            type="email"
            name="email_a"
            value={form.email_a}
            onChange={handleChange}
            required
            placeholder="partner-a@example.com"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">
            Partner B — Email
          </label>
          <input
            className="input"
            type="email"
            name="email_b"
            value={form.email_b}
            onChange={handleChange}
            required
            placeholder="partner-b@example.com"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">情侶名稱</label>
          <input
            className="input"
            type="text"
            name="couple_name"
            value={form.couple_name}
            onChange={handleChange}
            required
            placeholder="e.g. Dylan & Alex"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">
            紀念日（選填）
          </label>
          <input
            className="input"
            type="date"
            name="anniversary_date"
            value={form.anniversary_date}
            onChange={handleChange}
          />
        </div>

        {error && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">
            {error}
          </p>
        )}

        {success && (
          <pre className="whitespace-pre-wrap rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
            {success}
          </pre>
        )}

        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full"
        >
          {loading ? "送出中…" : "送出邀請"}
        </button>
      </form>

      <p className="text-center text-sm text-gray-400">
        已完成驗證？{" "}
        <button
          className="text-rose-500 underline"
          onClick={() => router.push("/register/complete")}
        >
          前往設定密碼
        </button>
      </p>
    </div>
  );
}
