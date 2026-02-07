'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div dir="rtl" style={{
      minHeight: '50vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
    }}>
      <div style={{ textAlign: 'center', maxWidth: '500px' }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚠️</div>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>خطا در بارگذاری صفحه</h2>
        <p style={{ color: '#9ca3af', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
          {error.message || 'مشکلی پیش آمد. لطفاً دوباره تلاش کنید.'}
        </p>
        <button
          onClick={() => reset()}
          style={{
            padding: '0.625rem 1.5rem',
            background: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '0.5rem',
            cursor: 'pointer',
            fontSize: '0.875rem',
          }}
        >
          تلاش مجدد
        </button>
      </div>
    </div>
  );
}
