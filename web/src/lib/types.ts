// Mirrors backend/app/schemas/auth.py

export interface RegisterInitiateRequest {
  email_a: string;
  email_b: string;
  couple_name: string;
  anniversary_date?: string; // ISO date string "YYYY-MM-DD"
}

export interface RegisterInitiateResponse {
  couple_id: string;
  message: string;
}

export interface RegisterVerifyRequest {
  token: string;
}

export interface RegisterVerifyResponse {
  email: string;
  verified: boolean;
  both_verified: boolean;
}

export interface RegisterCompleteRequest {
  couple_id: string;
  password_a: string;
  password_b: string;
  display_name_a: string;
  display_name_b: string;
}

export interface RegisterCompleteResponse {
  couple_id: string;
  message: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
