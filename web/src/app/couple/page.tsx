"use client";

import { useEffect, useRef, useState } from "react";
import { getCouple, updateCouple, uploadAvatar } from "@/lib/api";
import type { CoupleProfile } from "@/lib/types";

function getCoupleIdFromToken(): string | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem("pairspot_access_token");
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.couple_id ?? null;
  } catch {
    return null;
  }
}

export default function CouplePage() {
  const [couple, setCouple] = useState<CoupleProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Edit state
  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState("");
  const [editingDate, setEditingDate] = useState(false);
  const [dateInput, setDateInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  // Avatar upload
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    const coupleId = getCoupleIdFromToken();
    if (!coupleId) {
      setError("無法取得情侶 ID，請重新登入");
      setLoading(false);
      return;
    }
    getCouple(coupleId)
      .then((data) => {
        setCouple(data);
        setNameInput(data.couple_name);
        setDateInput(data.anniversary_date ?? "");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "載入失敗"))
      .finally(() => setLoading(false));
  }, []);

  async function saveName() {
    if (!couple) return;
    setSaving(true);
    setSaveError("");
    try {
      const updated = await updateCouple(couple.id, { couple_name: nameInput });
      setCouple(updated);
      setEditingName(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "儲存失敗");
    } finally {
      setSaving(false);
    }
  }

  async function saveDate() {
    if (!couple) return;
    setSaving(true);
    setSaveError("");
    try {
      const updated = await updateCouple(couple.id, {
        anniversary_date: dateInput || undefined,
      });
      setCouple(updated);
      setEditingDate(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "儲存失敗");
    } finally {
      setSaving(false);
    }
  }

  async function handleAvatarChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !couple) return;
    setUploading(true);
    setSaveError("");
    try {
      const updated = await uploadAvatar(couple.id, file);
      setCouple(updated);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "上傳失敗");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-rose-300 border-t-rose-600" />
      </div>
    );
  }

  if (error) {
    return (
      <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
    );
  }

  if (!couple) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">情侶檔案</h1>

      {saveError && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{saveError}</p>
      )}

      {/* Avatar */}
      <div className="flex flex-col items-center gap-3">
        <div className="relative">
          {couple.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={couple.avatar_url}
              alt="情侶頭貼"
              className="h-24 w-24 rounded-full object-cover border-2 border-rose-200"
            />
          ) : (
            <div className="flex h-24 w-24 items-center justify-center rounded-full bg-rose-100 text-3xl font-bold text-rose-400">
              {couple.couple_name[0]?.toUpperCase() ?? "?"}
            </div>
          )}
        </div>
        <button
          className="btn-secondary text-xs"
          disabled={uploading}
          onClick={() => fileRef.current?.click()}
        >
          {uploading ? "上傳中…" : "更換頭貼"}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleAvatarChange}
        />
      </div>

      {/* Days together */}
      <div className="rounded-lg border border-rose-100 bg-rose-50 p-4 text-center">
        <p className="text-4xl font-bold text-rose-600">{couple.days_together}</p>
        <p className="mt-1 text-sm text-rose-400">在一起天數</p>
      </div>

      {/* Couple name */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-xs font-medium text-gray-500">情侶名稱</span>
          {!editingName && (
            <button
              className="text-xs text-rose-500 hover:underline"
              onClick={() => {
                setNameInput(couple.couple_name);
                setEditingName(true);
              }}
            >
              編輯
            </button>
          )}
        </div>
        {editingName ? (
          <div className="flex gap-2">
            <input
              className="input flex-1 text-sm"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
            />
            <button className="btn-primary text-xs" disabled={saving} onClick={saveName}>
              {saving ? "…" : "儲存"}
            </button>
            <button
              className="btn-secondary text-xs"
              onClick={() => setEditingName(false)}
            >
              取消
            </button>
          </div>
        ) : (
          <p className="text-sm font-medium">{couple.couple_name}</p>
        )}
      </div>

      {/* Anniversary date */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-xs font-medium text-gray-500">紀念日</span>
          {!editingDate && (
            <button
              className="text-xs text-rose-500 hover:underline"
              onClick={() => {
                setDateInput(couple.anniversary_date ?? "");
                setEditingDate(true);
              }}
            >
              編輯
            </button>
          )}
        </div>
        {editingDate ? (
          <div className="flex gap-2">
            <input
              type="date"
              className="input flex-1 text-sm"
              value={dateInput}
              onChange={(e) => setDateInput(e.target.value)}
            />
            <button className="btn-primary text-xs" disabled={saving} onClick={saveDate}>
              {saving ? "…" : "儲存"}
            </button>
            <button
              className="btn-secondary text-xs"
              onClick={() => setEditingDate(false)}
            >
              取消
            </button>
          </div>
        ) : (
          <p className="text-sm">
            {couple.anniversary_date
              ? new Date(couple.anniversary_date + "T00:00:00").toLocaleDateString("zh-TW")
              : "尚未設定"}
          </p>
        )}
      </div>

      {/* Status */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <span className="text-xs font-medium text-gray-500">狀態</span>
        <p className="mt-1 text-sm">
          {couple.status === "active" && "✅ 正常"}
          {couple.status === "pending" && "⏳ 等待驗證"}
          {couple.status === "single" && "💔 已解除配對"}
          {couple.status === "suspended" && "⚠️ 已暫停"}
        </p>
      </div>
    </div>
  );
}
