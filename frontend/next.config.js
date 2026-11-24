/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  // PM-INS-0039: «اتاق فرمان» روی /oversight است. نامِ طبیعی‌اش (/command-room) را هر کسی
  // حدس می‌زند یا در پیام می‌نویسد — به‌جای ۴۰۴ به همان صفحه برود (query حفظ می‌شود).
  async redirects() {
    return [
      { source: '/command-room', destination: '/oversight', permanent: false },
      { source: '/command-room/:path*', destination: '/oversight', permanent: false },
    ];
  },
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
