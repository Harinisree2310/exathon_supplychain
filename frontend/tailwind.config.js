/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  'var(--brand-soft)',
          100: 'color-mix(in srgb, var(--brand-primary) 18%, white)',
          500: 'var(--brand-primary)',
          600: 'var(--brand-primary)',
          700: 'var(--brand-strong)',
          900: 'color-mix(in srgb, var(--brand-strong) 75%, black)',
        },
        risk: {
          low:    '#22c55e',
          medium: '#f59e0b',
          high:   '#ef4444',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
