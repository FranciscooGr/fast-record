/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0faf0',
          100: '#d6f0d6',
          200: '#aadcaa',
          300: '#72c272',
          400: '#3da63d',
          500: '#2d8a2d',
          600: '#1e6e1e',
          700: '#165416',
          800: '#0f3c0f',
          900: '#0a280a',
        },
        surface: {
          DEFAULT: '#f4f7f4',
          card:    '#ffffff',
          muted:   '#e8f0e8',
        },
        ink: {
          DEFAULT: '#111811',
          muted:   '#5a6e5a',
          faint:   '#9aaa9a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 2px 12px 0 rgba(0,0,0,0.07)',
        'card-hover': '0 6px 22px 0 rgba(0,0,0,0.12)',
      },
    },
  },
  plugins: [],
}


