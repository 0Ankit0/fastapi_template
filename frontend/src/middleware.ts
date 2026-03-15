import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Next.js Edge Middleware
 *
 * Responsibilities:
 * 1. Redirect unauthenticated users trying to access protected routes to /login.
 * 2. Redirect already-authenticated users away from auth pages to /dashboard.
 *
 * NOTE: Token *validity* (expiry, signature) is enforced server-side by the
 * FastAPI backend.  The middleware only checks for token *presence* so that we
 * can give users a fast redirect without a network round-trip.  The frontend
 * ProtectedRoute component and the api-client interceptors handle the full
 * refresh/re-auth flow once the page loads.
 *
 * Subscription enforcement happens in two layers:
 * - Backend: SubscriptionMiddleware (middleware.py) + require_active_subscription dependency.
 * - Frontend: SubscriptionGuard component wraps pages that need an active sub.
 *   The api-client interceptor redirects to /subscription on 402 responses.
 */

// Routes that require authentication.
const PROTECTED_PREFIXES = [
  '/dashboard',
  '/tenants',
  '/subscription',
  '/profile',
  '/settings',
  '/finances',
  '/notifications',
  '/tokens',
  '/rbac',
  '/admin',
];

// Auth-only routes: redirect authenticated users away.
const AUTH_ONLY_ROUTES = [
  '/login',
  '/signup',
  '/forgot-password',
  '/reset-password',
];

// Routes that bypass all checks (public assets, API routes, etc.)
const PUBLIC_PREFIXES = [
  '/_next',
  '/api',
  '/media',
  '/favicon.ico',
  '/payment-callback',
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip static/internal paths.
  if (PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return NextResponse.next();
  }

  // Detect token presence from localStorage is not possible in Edge middleware
  // (no DOM access).  Instead we look for the access_token in cookies as a
  // secondary indicator, but the primary check is the refresh_token cookie
  // (set by some SSR flows).  For most flows tokens live in localStorage, so
  // we rely on the ProtectedRoute component for the real gate and only do a
  // lightweight presence check here.
  const accessToken = request.cookies.get('access_token')?.value;
  const isAuthenticated = Boolean(accessToken);

  const isProtectedPath = PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  const isAuthOnlyPath = AUTH_ONLY_ROUTES.some((route) => pathname.startsWith(route));

  // Redirect unauthenticated users from protected pages to /login.
  if (isProtectedPath && !isAuthenticated) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('next', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Redirect authenticated users away from auth pages to /dashboard.
  if (isAuthOnlyPath && isAuthenticated) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  // Run middleware on all routes except Next.js internals and static files.
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
