/** @type {import('next').NextConfig} */
const { withSentryConfig } = require("@sentry/nextjs");

const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: { unoptimized: true },
  // 43P-FINAL-2: playwright-core é server-only (CDP remoto via connectOverCDP);
  // nunca deve ser bundled pelo webpack.
  serverExternalPackages: ['playwright-core'],
  webpack: (config) => {
    config.ignoreWarnings = [
      { module: /node_modules\/@supabase\/realtime-js/ },
    ];
    return config;
  },
};

module.exports = withSentryConfig(nextConfig, {
  silent: true,
  org: "smith-v2-lionlabs",
  project: "javascript-nextjs",
});