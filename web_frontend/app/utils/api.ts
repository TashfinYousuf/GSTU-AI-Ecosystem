import { createClient } from "./supabase/client";

// 🔴 Strictly use 127.0.0.1 to avoid browser CORS/Origin blocks
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();

  const headers = {
    "Content-Type": "application/json",
    // 🔴 ইউজার লগইন থাকলে অটোমেটিক টোকেন ব্যাকএন্ডে চলে যাবে
    ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "API request failed");
  }

  return data;
}