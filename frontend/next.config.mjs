/** @type {import('next').NextConfig} */
const apiTarget = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL;

if (process.env.NODE_ENV === "production" && !apiTarget) {
  throw new Error(
    "Missing API_INTERNAL_URL or NEXT_PUBLIC_API_URL for production build/runtime.",
  );
}

const nextConfig = {
  reactStrictMode: true,

  // Required for the Docker multi-stage build — produces a self-contained
  // server that can run without node_modules in the final image (~150 MB).
  output: "standalone",

  // Proxy API calls to FastAPI.
  // API_INTERNAL_URL is read at runtime (server-side), not baked in at build time.
  // NEXT_PUBLIC_API_URL is for client-side direct calls (fallback).
  async rewrites() {
    const target = apiTarget || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${target}/api/:path*`,
      },
      {
        source: "/data/:path*",
        destination: `${target}/data/:path*`,
      },
    ];
  },
};

export default nextConfig;
