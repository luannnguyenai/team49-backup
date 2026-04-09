// middleware.ts
// Next.js edge middleware — protects routes before they render

import { NextRequest, NextResponse } from "next/server";

// Routes that don't require authentication
const PUBLIC_PATHS = ["/login", "/register", "/"];

// Routes that require auth but NOT onboarding
const ONBOARDING_PATH = "/onboarding";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const accessToken = request.cookies.get("al_access_token")?.value;
  const isAuthenticated = Boolean(accessToken);

  // Allow public paths and static assets without auth check
  const isPublic =
    PUBLIC_PATHS.some((p) => pathname === p) ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon") ||
    pathname.includes(".");

  // ① Not authenticated → redirect to /login (except public routes)
  if (!isAuthenticated && !isPublic) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("from", pathname);
    return NextResponse.redirect(url);
  }

  // ② Authenticated but already going to login/register → redirect away
  if (isAuthenticated && (pathname === "/login" || pathname === "/register")) {
    // We can't read localStorage in the edge runtime, so redirect to /dashboard.
    // The protected layout will re-check onboarding status client-side.
    const url = request.nextUrl.clone();
    url.pathname = "/dashboard";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  // Run on every page request except Next.js internals
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
