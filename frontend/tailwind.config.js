/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        battery: {
          critical: '#EF4444',
          low: '#F97316',
          medium: '#EAB308',
          good: '#84CC16',
          full: '#22C55E',
        },
        station: {
          empty: '#9CA3AF',
          charging: '#3B82F6',
          full: '#22C55E',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
