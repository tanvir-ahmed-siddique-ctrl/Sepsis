/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // Single-container demo: browser calls /api and /fleet on the same origin.
  // Use `fallback` so Next BFF routes (/api/session, /api/hospital, /api/account,
  // /api/demo-accounts, …) win first; only unmatched /api/* goes to FastAPI.
  // A beforeFiles/default rewrite steals dynamic App Router handlers and returns
  // FastAPI's {"detail":"Not Found"} for sign-in.
  async rewrites() {
    const api = process.env.API_PROXY_TARGET;
    const fleet = process.env.FLEET_PROXY_TARGET;
    return {
      beforeFiles: [],
      afterFiles: [],
      fallback: [
        ...(api ? [{ source: "/api/:path*", destination: `${api}/:path*` }] : []),
        ...(fleet
          ? [
              { source: "/fleet", destination: `${fleet}/` },
              { source: "/fleet/:path*", destination: `${fleet}/:path*` },
            ]
          : []),
      ],
    };
  },
};

module.exports = nextConfig;
