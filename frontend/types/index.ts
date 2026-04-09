// types/index.ts
// Global TypeScript types shared across the app

export interface User {
  id: string;
  email: string;
  full_name: string;
  available_hours_per_week: number | null;
  target_deadline: string | null; // ISO date string YYYY-MM-DD
  preferred_method: "reading" | "video" | null;
  is_onboarded: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number; // seconds
}

export interface AccessToken {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// ---- Auth request shapes ----

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface OnboardingPayload {
  known_topic_ids: string[];
  desired_module_ids: string[];
  available_hours_per_week: number;
  target_deadline: string;
  preferred_method: "reading" | "video";
}

// ---- API error shape ----

export interface ApiError {
  detail: string | { msg: string; type: string }[];
}

// ---- Navigation ----

export interface NavItem {
  label: string;
  href: string;
  icon: string; // Lucide icon name
  badge?: number;
}
