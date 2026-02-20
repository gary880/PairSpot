import type {
  CoupleProfile,
  FeedResponse,
  LikeResponse,
  LoginRequest,
  LoginResponse,
  Post,
  RegisterCompleteRequest,
  RegisterCompleteResponse,
  RegisterInitiateRequest,
  RegisterInitiateResponse,
  RegisterVerifyResponse,
  UserAccount,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Error parsing ───────────────────────────────────────────────────────────

type FastAPIError = { detail: string | Array<{ msg: string }> };

async function parseError(res: Response): Promise<string> {
  try {
    const body: FastAPIError = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((e) => e.msg).join("; ");
    }
    return `HTTP ${res.status}`;
  } catch {
    return `HTTP ${res.status}`;
  }
}

// ── Auth token helper ────────────────────────────────────────────────────────

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("pairspot_access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── Generic fetch helpers ────────────────────────────────────────────────────

async function post<TReq, TRes>(path: string, body: TReq): Promise<TRes> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<TRes>;
}

async function authGet<TRes>(path: string): Promise<TRes> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<TRes>;
}

async function authPost<TRes>(
  path: string,
  body?: Record<string, unknown>
): Promise<TRes> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<TRes>;
}

async function authPostMultipart<TRes>(
  path: string,
  formData: FormData
): Promise<TRes> {
  // No Content-Type header — browser sets multipart/form-data with boundary
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { ...authHeaders() },
    body: formData,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<TRes>;
}

async function authPatch<TRes>(
  path: string,
  body?: Record<string, unknown>
): Promise<TRes> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<TRes>;
}

async function authPutMultipart<TRes>(
  path: string,
  formData: FormData
): Promise<TRes> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "PUT",
    headers: { ...authHeaders() },
    body: formData,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<TRes>;
}

async function authDelete<TRes>(path: string): Promise<TRes> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<TRes>;
}

async function authDeleteNoContent(path: string): Promise<void> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(await parseError(res));
}

// ── Auth API ─────────────────────────────────────────────────────────────────

export function registerInitiate(
  data: RegisterInitiateRequest
): Promise<RegisterInitiateResponse> {
  return post<RegisterInitiateRequest, RegisterInitiateResponse>(
    "/api/v1/auth/register/initiate",
    data
  );
}

export function registerVerify(token: string): Promise<RegisterVerifyResponse> {
  return post<{ token: string }, RegisterVerifyResponse>(
    "/api/v1/auth/register/verify",
    { token }
  );
}

export function registerComplete(
  data: RegisterCompleteRequest
): Promise<RegisterCompleteResponse> {
  return post<RegisterCompleteRequest, RegisterCompleteResponse>(
    "/api/v1/auth/register/complete",
    data
  );
}

export function login(data: LoginRequest): Promise<LoginResponse> {
  return post<LoginRequest, LoginResponse>("/api/v1/auth/login", data);
}

// ── Posts API ─────────────────────────────────────────────────────────────────

export function getFeed(offset = 0, limit = 20): Promise<FeedResponse> {
  return authGet<FeedResponse>(
    `/api/v1/posts?offset=${offset}&limit=${limit}`
  );
}

export function createPost(formData: FormData): Promise<Post> {
  return authPostMultipart<Post>("/api/v1/posts", formData);
}

export function likePost(postId: string): Promise<LikeResponse> {
  return authPost<LikeResponse>(`/api/v1/posts/${postId}/like`);
}

export function unlikePost(postId: string): Promise<LikeResponse> {
  return authDelete<LikeResponse>(`/api/v1/posts/${postId}/like`);
}

// ── Couples API ───────────────────────────────────────────────────────────────

export function getCouple(coupleId: string): Promise<CoupleProfile> {
  return authGet<CoupleProfile>(`/api/v1/couples/${coupleId}`);
}

export function updateCouple(
  coupleId: string,
  data: { couple_name?: string; anniversary_date?: string }
): Promise<CoupleProfile> {
  return authPatch<CoupleProfile>(`/api/v1/couples/${coupleId}`, data as Record<string, unknown>);
}

export function uploadAvatar(
  coupleId: string,
  file: File
): Promise<CoupleProfile> {
  const formData = new FormData();
  formData.append("file", file);
  return authPutMultipart<CoupleProfile>(`/api/v1/couples/${coupleId}/avatar`, formData);
}

// ── Account API ───────────────────────────────────────────────────────────────

export function getAccount(): Promise<UserAccount> {
  return authGet<UserAccount>("/api/v1/account");
}

export function updateAccount(data: { display_name?: string }): Promise<UserAccount> {
  return authPatch<UserAccount>("/api/v1/account", data as Record<string, unknown>);
}

export function deleteAccount(): Promise<void> {
  return authDeleteNoContent("/api/v1/account");
}

export function restoreAccount(): Promise<UserAccount> {
  return authPost<UserAccount>("/api/v1/account/restore");
}
