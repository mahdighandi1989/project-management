import type { Metadata } from 'next';
import Layout from '@/components/Layout';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'سیستم مناظره و همکاری AI',
  description: 'سیستم مناظره و همکاری هوش مصنوعی + مدیریت پروژه',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fa" dir="rtl">
      <body>
        <Layout>{children}</Layout>
      </body>
    </html>
  );
}
