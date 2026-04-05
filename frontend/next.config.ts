import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactCompiler: true,
  output: 'standalone',
  async rewrites() {
    const internalApiBaseUrl =
      process.env.INTERNAL_API_BASE_URL ?? 'http://localhost:8000';

    return [
      {
        source: '/api/v1/:path*',
        destination: `${internalApiBaseUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
