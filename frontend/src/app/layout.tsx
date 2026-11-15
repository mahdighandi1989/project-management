import type { Metadata } from 'next';
import Script from 'next/script';
import Layout from '@/components/Layout';
import { APP_NAME, APP_NAME_FA, APP_TAGLINE } from '@/lib/siteMap';
import { HelpProvider, HelpSystem } from '@/components/help';
import '@/styles/globals.css';

import InspectorBridge from "./InspectorBridge";
import { AuthGate } from '@/lib/auth';

export const metadata: Metadata = {
  title: `${APP_NAME} — ${APP_NAME_FA}`,
  description: APP_TAGLINE,
  icons: {
    icon: '/icon.svg',
  },
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
      <body>
        <Script
          id="runtime-config"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `window.__NEXT_PUBLIC_API_URL__ = "${apiUrl}";`,
          }}
        />
        {/* ورود با گوگل — nothing renders until signed in (when enforced) */}
        <AuthGate>
          <HelpProvider>
            <Layout>
              <InspectorBridge />
              {children}
            </Layout>
            <HelpSystem />
          </HelpProvider>
        </AuthGate>
      </body>
    </html>
  );
}
