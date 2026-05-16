// middleware.ts
// Next.js edge middleware — protects routes before they render
//
// Access policy:
// - Guests can only view the marketing landing page and auth/reset pages.
// - App/navigation routes require authentication.
// - Authenticated users are kept out of auth pages and the public landing page.

import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login", "/register", "/forgot-password", "/reset-password", "/"];
const REDIRECT_AUTHENTICATED_AUTH_PATHS = ["/login", "/register"];

function isSafeInternalRedirectTarget(redirectTo: string | null): redirectTo is string {
  return Boolean(redirectTo && redirectTo.startsWith("/") && !redirectTo.startsWith("//"));
}

function applyRelativeRedirectTarget(url: URL, redirectTo: string | null): void {
  if (!isSafeInternalRedirectTarget(redirectTo)) {
    url.pathname = "/dashboard";
    url.search = "";
    return;
  }

  const resolved = new URL(redirectTo, url.origin);
  url.pathname = resolved.pathname;
  url.search = resolved.search;
}

/**
 * Check if a pathname matches a public route.
 * - Exact matches for PUBLIC_PATHS
 * - Static assets and Next.js internals
 */
function isPublicPath(pathname: string): boolean {
  if (PUBLIC_PATHS.some((p) => pathname === p)) return true;

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

  // ① Guests should land on the marketing page until they choose to sign in.
  if (!isAuthenticated && !isPublic) {
    const url = request.nextUrl.clone();
    url.pathname = "/";
    url.search = "";
    return NextResponse.redirect(url);
  }

  // ② Authenticated but already going to auth pages → redirect away
  if (isAuthenticated && REDIRECT_AUTHENTICATED_AUTH_PATHS.includes(pathname)) {
    const url = request.nextUrl.clone();
    // If there's a redirect param, honor it instead of dashboard.
    const redirectTo = searchParams.get("next") || searchParams.get("from");
    applyRelativeRedirectTarget(url, redirectTo);
    return NextResponse.redirect(url);
  }

  // ③ Authenticated users should not land on the public marketing homepage.
  if (isAuthenticated && pathname === "/") {
    const url = request.nextUrl.clone();
    url.pathname = "/agent";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  // Run on every page request except Next.js internals
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
