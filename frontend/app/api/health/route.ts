// app/api/health/route.ts
// Health check endpoint used by Docker HEALTHCHECK and monitoring tools.

import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json(
    { status: "ok", timestamp: new Date().toISOString() },
    { status: 200 }
  );
}
