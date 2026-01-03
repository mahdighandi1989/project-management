import type { Metadata } from 'next';
import Script from 'next/script';
import Layout from '@/components/Layout';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'سیستم مناظره و همکاری AI',
  description: 'سیستم مناظره و همکاری هوش مصنوعی + مدیریت پروژه',
};

// Get API URL for runtime injection
const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fa" dir="rtl">
      <head>
        <Script
          id="runtime-config"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `window.__NEXT_PUBLIC_API_URL__ = "${apiUrl}";`,
          }}
        />
      </head>
      <body>
        <Layout>{children}</Layout>
      </body>
    </html>
  );
}
