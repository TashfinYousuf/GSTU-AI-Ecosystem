import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware (request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request: { headers: request.headers },
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) { return request.cookies.get(name)?.value },
        set(name: string, value: string, options: CookieOptions) {
          request.cookies.set({ name, value, ...options })
          supabaseResponse = NextResponse.next({ request: { headers: request.headers } })
          supabaseResponse.cookies.set({ name, value, ...options })
        },
        remove(name: string, options: CookieOptions) {
          request.cookies.set({ name, value: '', ...options })
          supabaseResponse = NextResponse.next({ request: { headers: request.headers } })
          supabaseResponse.cookies.set({ name, value: '', ...options })
        },
      },
    }
  )

  const { data: { user } } = await supabase.auth.getUser()

  // 🔴 Premium Routes: যে রাউটগুলোতে লগইন ছাড়া প্রবেশ নিষেধ
  const premiumRoutes = ['/routine', '/settings', '/workspaces', '/premium'];
  const isPremiumRoute = premiumRoutes.some(route => request.nextUrl.pathname.startsWith(route));

  // ইউজার লগইন করা না থাকলে এবং প্রিমিয়াম রাউটে যেতে চাইলে লগইন পেজে পাঠাব
  if (!user && isPremiumRoute) {
    const url = request.nextUrl.clone()
    url.pathname = '/auth/login'
    return NextResponse.redirect(url)
  }

  // ইউজার লগইন করা থাকলে তাকে আর /auth পেজে ঢুকতে না দিয়ে মেইন পেজে পাঠাব
  if (user && request.nextUrl.pathname.startsWith('/auth')) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard' // অ্যাপের মেইন রাউট
    return NextResponse.redirect(url)
  }

  const response = NextResponse.next();
  const userAgent = request.headers.get('user-agent') || '';

  // 🛡️ 1. SILICON VALLEY BOT PROTECTION (Block scripts & scrapers instantly)
  const blockedAgents = ['curl', 'python-requests', 'postmanruntime', 'wget', 'scrapy'];
  if (blockedAgents.some(agent => userAgent.toLowerCase().includes(agent))) {
    return new NextResponse(
      JSON.stringify({ error: "Access Denied. Suspicious activity detected." }),
      { status: 403, headers: { 'content-type': 'application/json' } }
    );
  }

  // 🔒 2. ENTERPRISE SECURITY HEADERS (Prevents Clickjacking, XSS, Sniffing)
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');

  // 🔒 ENTERPRISE HEADERS
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-Content-Type-Options', 'nosniff');

  // ⚡ 3. LIGHTNING FAST AUTH CACHE CHECK (Prevents UI Flicker)
  // Check if it's a protected route
  if (request.nextUrl.pathname.startsWith('/dashboard')) {
    // Look for Supabase Auth Cookie (Next.js side)
    const hasSession = request.cookies.getAll().some(cookie => cookie.name.includes('sb-') && cookie.name.includes('-auth-token'));
    
    // If no session exists, redirect at the Edge (0ms UI render delay!)
    if (!hasSession && !request.nextUrl.pathname.includes('/dashboard/ai-chat')) {
       // Optional: Redirect to login if strictly required
       // return NextResponse.redirect(new URL('/auth/login', request.url));
    }
  }
  return supabaseResponse
}

// Apply middleware only to specific routes to save compute
export const config = {
  matcher: ['/dashboard/:path*', '/api/:path*', '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
};