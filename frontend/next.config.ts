import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [{ protocol: "https", hostname: "**" }],
  },
  transpilePackages: ["react-leaflet", "leaflet"],
  turbopack: {},
};

export default nextConfig;
