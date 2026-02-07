'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="fa" dir="rtl">
      <body>
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#111827',
          color: 'white',
          fontFamily: 'system-ui, sans-serif',
        }}>
          <div style={{ textAlign: 'center', maxWidth: '500px', padding: '2rem' }}>
            <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>⚠️</div>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>خطای غیرمنتظره</h2>
            <p style={{ color: '#9ca3af', marginBottom: '1.5rem' }}>
              مشکلی در بارگذاری صفحه پیش آمد. لطفاً دوباره تلاش کنید.
            </p>
            <button
              onClick={() => reset()}
              style={{
                padding: '0.75rem 2rem',
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                fontSize: '1rem',
              }}
            >
              تلاش مجدد
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
