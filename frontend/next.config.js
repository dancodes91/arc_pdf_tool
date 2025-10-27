/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  allowedDevOrigins: ['127.0.0.1:3000'],
  webpack: (config, { isServer }) => {
    // Ignore Windows system files that cause Watchpack errors
    config.watchOptions = {
      ...config.watchOptions,
      ignored: [
        '**/node_modules/**',
        '**/.git/**',
        '**/C:/hiberfil.sys',
        '**/C:/pagefile.sys',
        '**/C:/swapfile.sys',
        '**/C:/DumpStack.log.tmp',
      ],
    };
    return config;
  },
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
