import type { NextConfig } from "next";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // 📦 2. Optimize images heavily
  images: {
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 604800, // Cache images for a week!
  },

  compiler: {
    // 🗑️ 3. Strip all console.logs in production (Massive speed boost on client)
    removeConsole: process.env.NODE_ENV === 'production' ? { exclude: ['error'] } : false,
  },

  // 🗜️ 4. Compress responses with Brotli/Gzip automatically
  compress: true,
};

export default nextConfig;