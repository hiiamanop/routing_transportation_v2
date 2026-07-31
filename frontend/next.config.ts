import type { NextConfig } from "next";

// URL internal ke Flask API. Di Docker Compose ini di-override jadi
// http://api:5001 (nama service, bukan localhost) lewat env var.
const API_INTERNAL_URL = process.env.API_INTERNAL_URL || "http://localhost:5001";

const nextConfig: NextConfig = {
  async rewrites() {
    // Array biasa = "afterFiles": filesystem route Next.js sendiri (spt
    // /api/search-places) tetap diprioritaskan, cuma path yang TIDAK match
    // route lokal yang diteruskan ke Flask. Jadi tidak butuh nginx terpisah.
    return [{ source: "/api/:path*", destination: `${API_INTERNAL_URL}/api/:path*` }];
  },
};

export default nextConfig;
