/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // Single-container demo: the browser calls /api (hospital API) and /fleet (vendor
  // console) on the same origin and Next forwards them to processes inside the
  // container. Read at build time; unset for the normal stacks.
  async rewrites() {
    const api = process.env.API_PROXY_TARGET;
    const fleet = process.env.FLEET_PROXY_TARGET;
    return [
      ...(api ? [{ source: "/api/:path*", destination: `${api}/:path*` }] : []),
      ...(fleet
        ? [
            { source: "/fleet", destination: `${fleet}/` },
            { source: "/fleet/:path*", destination: `${fleet}/:path*` },
          ]
        : []),
    ];
  },
};

module.exports = nextConfig;
