// Mirrors backend/app/schemas/auth.py + schemas/post.py

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

// ── Post types ──────────────────────────────────────────────────────────────

export interface PostImage {
  id: string;
  image_url: string;
  thumbnail_url: string | null;
  sort_order: number;
  width: number | null;
  height: number | null;
}

export interface PostAuthor {
  id: string;
  display_name: string;
  role: string;
}

export interface Post {
  id: string;
  couple_id: string;
  author_id: string;
  author: PostAuthor;
  content: string | null;
  visibility: "public" | "private";
  is_promoted: boolean;
  promoted_until: string | null;
  like_count: number;
  liked_by_me: boolean;
  images: PostImage[];
  created_at: string;
  updated_at: string | null;
}

export interface FeedResponse {
  items: Post[];
  total: number;
  offset: number;
  limit: number;
}

export interface LikeResponse {
  liked: boolean;
  like_count: number;
}

// ── Couple types ─────────────────────────────────────────────────────────────

export interface CoupleProfile {
  id: string;
  couple_name: string;
  anniversary_date: string | null; // ISO date "YYYY-MM-DD"
  avatar_url: string | null;
  status: "pending" | "active" | "suspended" | "single";
  days_together: number;
  created_at: string;
  updated_at: string | null;
}

// ── Account types ─────────────────────────────────────────────────────────────

export interface UserAccount {
  id: string;
  email: string;
  display_name: string;
  role: "partner_a" | "partner_b";
  email_verified: boolean;
  created_at: string;
  updated_at: string | null;
}
