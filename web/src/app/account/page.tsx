"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { deleteAccount, getAccount, restoreAccount, updateAccount } from "@/lib/api";
import type { UserAccount } from "@/lib/types";

export default function AccountPage() {
  const router = useRouter();
  const [account, setAccount] = useState<UserAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isDeleted, setIsDeleted] = useState(false);

  // Edit display_name
  const [editing, setEditing] = useState(false);
  const [nameInput, setNameInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  // Delete / restore
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [restoring, setRestoring] = useState(false);

  useEffect(() => {
    getAccount()
      .then((data) => {
        setAccount(data);
        setNameInput(data.display_name);
      })
      .catch((err) => {
        const msg = err instanceof Error ? err.message : "載入失敗";
        // If 401, account may be deleted — try restore flow
        if (msg.includes("401") || msg.toLowerCase().includes("unauthorized")) {
          setIsDeleted(true);
        } else {
          setError(msg);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  async function saveName() {
    if (!account) return;
    setSaving(true);
    setSaveError("");
    try {
      const updated = await updateAccount({ display_name: nameInput });
      setAccount(updated);
      setEditing(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "儲存失敗");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    setSaveError("");
    try {
      await deleteAccount();
      router.push("/login");
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "刪除失敗");
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  }

  async function handleRestore() {
    setRestoring(true);
    setSaveError("");
    try {
      const restored = await restoreAccount();
      setAccount(restored);
      setNameInput(restored.display_name);
      setIsDeleted(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "恢復失敗");
    } finally {
      setRestoring(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-rose-300 border-t-rose-600" />
      </div>
    );
  }

  // Deleted account — show restore UI
  if (isDeleted) {
    return (
      <div className="space-y-4">
        <h1 className="text-lg font-semibold">帳號管理</h1>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-center space-y-3">
          <p className="text-sm text-amber-700 font-medium">您的帳號已被刪除</p>
          <p className="text-xs text-amber-600">刪除後 30 天內可恢復帳號</p>
          {saveError && (
            <p className="text-sm text-red-600">{saveError}</p>
          )}
          <button
            className="btn-primary w-full"
            disabled={restoring}
            onClick={handleRestore}
          >
            {restoring ? "恢復中…" : "恢復帳號"}
          </button>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
    );
  }

  if (!account) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">帳號管理</h1>

      {saveError && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{saveError}</p>
      )}

      {/* Email */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <span className="text-xs font-medium text-gray-500">電子郵件</span>
        <div className="mt-1 flex items-center gap-2">
          <p className="text-sm">{account.email}</p>
          {account.email_verified ? (
            <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-700">已驗證</span>
          ) : (
            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-700">未驗證</span>
          )}
        </div>
      </div>

      {/* Display name */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-xs font-medium text-gray-500">顯示名稱</span>
          {!editing && (
            <button
              className="text-xs text-rose-500 hover:underline"
              onClick={() => {
                setNameInput(account.display_name);
                setEditing(true);
              }}
            >
              編輯
            </button>
          )}
        </div>
        {editing ? (
          <div className="flex gap-2">
            <input
              className="input flex-1 text-sm"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
            />
            <button className="btn-primary text-xs" disabled={saving} onClick={saveName}>
              {saving ? "…" : "儲存"}
            </button>
            <button className="btn-secondary text-xs" onClick={() => setEditing(false)}>
              取消
            </button>
          </div>
        ) : (
          <p className="text-sm font-medium">{account.display_name}</p>
        )}
      </div>

      {/* Role */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <span className="text-xs font-medium text-gray-500">角色</span>
        <p className="mt-1 text-sm">
          {account.role === "partner_a" ? "Partner A" : "Partner B"}
        </p>
      </div>

      {/* Joined */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <span className="text-xs font-medium text-gray-500">加入時間</span>
        <p className="mt-1 text-sm">
          {new Date(account.created_at).toLocaleDateString("zh-TW")}
        </p>
      </div>

      {/* Delete account */}
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="mb-2 text-sm font-medium text-red-700">危險區域</p>
        <p className="mb-3 text-xs text-red-500">
          刪除帳號後，您的情侶狀態將降為單身。30 天內可恢復。
        </p>
        {!showDeleteConfirm ? (
          <button
            className="w-full rounded-md border border-red-400 bg-white px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
            onClick={() => setShowDeleteConfirm(true)}
          >
            刪除帳號
          </button>
        ) : (
          <div className="space-y-2">
            <p className="text-sm font-medium text-red-700">確定要刪除帳號嗎？</p>
            <div className="flex gap-2">
              <button
                className="flex-1 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                disabled={deleting}
                onClick={handleDelete}
              >
                {deleting ? "刪除中…" : "確認刪除"}
              </button>
              <button
                className="btn-secondary flex-1 text-sm"
                onClick={() => setShowDeleteConfirm(false)}
              >
                取消
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
