// middleware.ts
// Next.js edge middleware — protects routes before they render
//
// US2 changes:
// - Course overview pages (/courses/*) are public
// - Preserve course context through auth redirects via ?next= param

import { NextRequest, NextResponse } from "next/server";

// Routes that don't require authentication
const PUBLIC_PATHS = ["/login", "/register", "/"];

// Routes that require auth but NOT onboarding
const ONBOARDING_PATH = "/onboarding";

/**
 * Check if a pathname matches a public route.
 * - Exact matches for PUBLIC_PATHS
 * - Course overview pages (/courses/{slug}) are public
 * - Static assets and Next.js internals
 */
function isPublicPath(pathname: string): boolean {
  // Exact public paths
  if (PUBLIC_PATHS.some((p) => pathname === p)) return true;

  // Course catalog and overview pages are public (but not /courses/*/learn/*)
  if (pathname.startsWith("/courses/") && !pathname.includes("/learn/")) return true;

  // Static assets and Next.js internals
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon") ||
    pathname.includes(".")
  )
    return true;

  return false;
}

export function middleware(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;

  const accessToken = request.cookies.get("al_access_token")?.value;
  const isAuthenticated = Boolean(accessToken);
  const isPublic = isPublicPath(pathname);

  // ① Not authenticated → redirect to /login (except public routes)
  if (!isAuthenticated && !isPublic) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    // Preserve the original destination including any ?next= param
    const nextPath = searchParams.get("next") || pathname;
    url.searchParams.set("from", nextPath);
    return NextResponse.redirect(url);
  }

  // ② Authenticated but already going to login/register → redirect away
  if (isAuthenticated && (pathname === "/login" || pathname === "/register")) {
    const url = request.nextUrl.clone();
    // If there's a "from" param, redirect there instead of dashboard
    const from = searchParams.get("from");
    url.pathname = from || "/dashboard";
    url.searchParams.delete("from");
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  // Run on every page request except Next.js internals
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
