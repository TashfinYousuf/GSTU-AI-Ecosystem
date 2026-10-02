import { createClient } from "./supabase/client";

// Normalize base URL so it NEVER ends with /api/v1 or trailing slashes
export const getBaseServerUrl = (): string => {
  let base = process.env.NEXT_PUBLIC_API_URL || (
    typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
      ? "http://localhost:8000"
      : "https://gstu-ai-backend.onrender.com"
  );
  base = base.replace(/\/+$/, "");
  if (base.endsWith("/api/v1")) {
    base = base.slice(0, -"/api/v1".length);
  }
  return base;
};

// Returns standard base URL ending with /api/v1
export const getBaseApiUrl = (): string => {
  return `${getBaseServerUrl()}/api/v1`;
};

export const BASE_URL = getBaseApiUrl();

// Builds a safe, canonical URL ensuring exactly ONE /api/v1 prefix
export const buildApiUrl = (endpoint: string): string => {
  const base = getBaseServerUrl();
  let cleanEndpoint = (endpoint || "").trim();
  while (cleanEndpoint.startsWith("/api/v1")) {
    cleanEndpoint = cleanEndpoint.slice("/api/v1".length);
  }
  if (!cleanEndpoint.startsWith("/")) {
    cleanEndpoint = `/${cleanEndpoint}`;
  }
  return `${base}/api/v1${cleanEndpoint}`;
};

export async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();

  const headers = {
    "Content-Type": "application/json",
    // Authenticated Supabase session token
    ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
    ...options.headers,
  };

  const isGet = !options.method || options.method.toUpperCase() === "GET";
  
  const fetchOptions: RequestInit = {
    ...options,
    headers,
    cache: isGet ? "default" : "no-store",
    next: isGet ? { revalidate: 60 } : { revalidate: 0 },
  };

  const primaryUrl = buildApiUrl(endpoint);

  try {
    let response: Response;
    
    try {
      response = await fetch(primaryUrl, fetchOptions);
    } catch (networkErr: any) {
      // Automatic fallback if localhost or Render is unreachable
      if (typeof window !== "undefined") {
        const isLocal = primaryUrl.includes("localhost") || primaryUrl.includes("127.0.0.1");
        let cleanEndpoint = (endpoint || "").trim();
        while (cleanEndpoint.startsWith("/api/v1")) {
          cleanEndpoint = cleanEndpoint.slice("/api/v1".length);
        }
        if (!cleanEndpoint.startsWith("/")) cleanEndpoint = `/${cleanEndpoint}`;

        const fallbackBase = isLocal 
          ? "https://gstu-ai-backend.onrender.com/api/v1" 
          : "http://localhost:8000/api/v1";
        const fallbackUrl = `${fallbackBase}${cleanEndpoint}`;

        console.warn(`[fetchAPI] Primary ${primaryUrl} failed (${networkErr.message}). Retrying fallback: ${fallbackUrl}`);
        response = await fetch(fallbackUrl, fetchOptions);
      } else {
        throw networkErr;
      }
    }

    const data = await response.json();

    if (!response.ok) {
      let errorMessage = "API request failed";
      
      // Properly parse FastAPI 422 Validation Array
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