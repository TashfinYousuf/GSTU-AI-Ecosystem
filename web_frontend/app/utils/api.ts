import { createClient } from "./supabase/client";

// 🔴 Strictly use 127.0.0.1 to avoid browser CORS/Origin blocks locally
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

  // ⚡ 1. SMART CACHING STRATEGY: 
  // GET requests are cached for 60s at the Edge. POST/PUT bypass cache.
  const isGet = !options.method || options.method.toUpperCase() === "GET";
  
  const fetchOptions: RequestInit = {
    ...options,
    headers,
    cache: isGet ? "default" : "no-store",
    next: isGet ? { revalidate: 60 } : { revalidate: 0 },
  };

  try {
    const response = await fetch(`${BASE_URL}${endpoint}`, fetchOptions);
    const data = await response.json();

    if (!response.ok) {
      let errorMessage = "API request failed";
      
      // 🔴 Properly parse FastAPI 422 Validation Array
      if (Array.isArray(data.detail)) {
        errorMessage = data.detail.map((err: any) => `${err.loc.join('.')}: ${err.msg}`).join(' | ');
      } else if (data.detail) {
        errorMessage = data.detail;
      } else if (data.message) {
        errorMessage = data.message;
      }
      
      throw new Error(errorMessage);
    }

    return data;
  } catch (error: any) {
    console.error(`[API Error] ${endpoint}:`, error);
    throw error;
  }
}