import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
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

  return supabaseResponse
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}