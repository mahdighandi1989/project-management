/** @type {import('tailwindcss').Config} */
module.exports = {
  // 🩹 (2026-11-15) «اتاق فرمان» settings chips build class names at run time (`bg-${color}-50` …) — the build cannot
  // see them, so they were stripped and the chips rendered unstyled. Keep exactly those.
  safelist: [
    'bg-cyan-50',
    'dark:bg-cyan-900/20',
    'text-cyan-700',
    'dark:text-cyan-300',
    'border-cyan-300',
    'dark:border-cyan-700',
    'hover:bg-cyan-100',
    'dark:hover:bg-cyan-900/40',
    'ring-cyan-400',
    'bg-fuchsia-50',
    'dark:bg-fuchsia-900/20',
    'text-fuchsia-700',
    'dark:text-fuchsia-300',
    'border-fuchsia-300',
    'dark:border-fuchsia-700',
    'hover:bg-fuchsia-100',
    'dark:hover:bg-fuchsia-900/40',
    'ring-fuchsia-400',
    'bg-teal-50',
    'dark:bg-teal-900/20',
    'text-teal-700',
    'dark:text-teal-300',
    'border-teal-300',
    'dark:border-teal-700',
    'hover:bg-teal-100',
    'dark:hover:bg-teal-900/40',
    'ring-teal-400',
    'bg-amber-50',
    'dark:bg-amber-900/20',
    'text-amber-700',
    'dark:text-amber-300',
    'border-amber-300',
    'dark:border-amber-700',
    'hover:bg-amber-100',
    'dark:hover:bg-amber-900/40',
    'ring-amber-400',
  ],
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        },
      },
      fontFamily: {
        'vazir': ['Vazirmatn', 'Tahoma', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
      },
      keyframes: {
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: 0 },
          '100%': { transform: 'translateY(0)', opacity: 1 },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: 0 },
          '100%': { transform: 'translateY(0)', opacity: 1 },
        },
      },
    },
  },
  plugins: [],
}
