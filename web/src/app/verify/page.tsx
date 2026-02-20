"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { registerVerify } from "@/lib/api";

type Status = "loading" | "success-one" | "success-both" | "error";

function VerifyContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<Status>("loading");
  const [email, setEmail] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setErrorMsg("URL 中缺少 token 參數。");
      setStatus("error");
      return;
    }

    registerVerify(token)
      .then((res) => {
        setEmail(res.email);
        if (res.both_verified) {
          setStatus("success-both");
        } else {
          setStatus("success-one");
        }
      })
      .catch((err: unknown) => {
        setErrorMsg(err instanceof Error ? err.message : "驗證失敗");
        setStatus("error");
      });
  }, [searchParams]);

  function goToComplete() {
    const coupleId = localStorage.getItem("pairspot_couple_id") ?? "";
    const path = coupleId
      ? `/register/complete?couple_id=${coupleId}`
      : "/register/complete";
    router.push(path);
  }

  if (status === "loading") {
    return (
      <div className="flex flex-col items-center gap-4 py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-rose-300 border-t-rose-600" />
        <p className="text-sm text-gray-500">驗證中，請稍候…</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-rose-600">PairSpot</h1>
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm font-semibold text-red-700">驗證失敗</p>
          <p className="mt-1 text-sm text-red-600">{errorMsg}</p>
          <p className="mt-2 text-xs text-gray-400">
            Token 可能已過期或已使用。請重新發起註冊流程。
          </p>
        </div>
        <button
          className="btn-secondary w-full"
          onClick={() => router.push("/register")}
        >
          返回重新註冊
        </button>
      </div>
    );
  }

  if (status === "success-one") {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-rose-600">PairSpot</h1>
        <div className="rounded-md bg-yellow-50 p-4">
          <p className="text-sm font-semibold text-yellow-800">
            ✅ {email} 驗證成功！
          </p>
          <p className="mt-2 text-sm text-yellow-700">
            等待另一半也完成 Email 驗證後，即可設定密碼。
          </p>
        </div>
        <p className="text-xs text-gray-400">
          另一半驗證完畢後，請點擊其驗證信中的連結，系統將自動跳轉至設定頁面。
        </p>
      </div>
    );
  }

  // success-both
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-rose-600">PairSpot</h1>
      <div className="rounded-md bg-green-50 p-4">
        <p className="text-sm font-semibold text-green-800">
          🎉 雙方 Email 皆已驗證完成！
        </p>
        <p className="mt-1 text-sm text-green-700">
          {email} 驗證成功。現在可以設定雙方的顯示名稱與密碼。
        </p>
      </div>
      <button className="btn-primary w-full" onClick={goToComplete}>
        前往設定密碼
      </button>
    </div>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<p className="text-sm text-gray-400">載入中…</p>}>
      <VerifyContent />
    </Suspense>
  );
}
