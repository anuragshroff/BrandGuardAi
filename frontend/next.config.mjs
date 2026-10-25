/** @type {import('next').NextConfig} */
const staticExport = process.env.NEXT_STATIC_EXPORT === "1";

const nextConfig = {
  reactStrictMode: true,
  // `NEXT_STATIC_EXPORT=1` produces `out/` which FastAPI serves from the same
  // origin as the API. Local development keeps the normal Next server.
  ...(staticExport
    ? {
        output: "export",
        trailingSlash: true,
        images: { unoptimized: true },
      }
    : {}),
};

export default nextConfig;
