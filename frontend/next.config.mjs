import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,

  // Required for the Docker multi-stage build — produces a self-contained
  // server that can run without node_modules in the final image (~150 MB).
  output: "standalone",

  // Proxy API calls to FastAPI in development (avoids CORS issues)
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
