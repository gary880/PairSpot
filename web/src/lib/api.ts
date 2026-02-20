import type {
  LoginRequest,
  LoginResponse,
  RegisterCompleteRequest,
  RegisterCompleteResponse,
  RegisterInitiateRequest,
  RegisterInitiateResponse,
  RegisterVerifyResponse,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

async function post<TReq, TRes>(path: string, body: TReq): Promise<TRes> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await parseError(res);
    throw new Error(detail);
  }
  return res.json() as Promise<TRes>;
}

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
