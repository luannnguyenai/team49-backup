/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Required for the Docker multi-stage build — produces a self-contained
  // server that can run without node_modules in the final image (~150 MB).
  output: "standalone",

  // Proxy API calls to FastAPI.
  // API_INTERNAL_URL is read at runtime (server-side), not baked in at build time.
  // NEXT_PUBLIC_API_URL is for client-side direct calls (fallback).
  async rewrites() {
    const target =
      process.env.API_INTERNAL_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000";
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
