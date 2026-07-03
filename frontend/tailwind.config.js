/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#0b0f19', // sleek neon-dark base navy
          dark: '#05070a',
          light: '#141b2c',
          card: '#111827'
        },
        accent: {
          DEFAULT: '#f59e0b', // amber orange
          hover: '#d97706',
          light: '#fef3c7'
        }
      }
    },
  },
  plugins: [],
}
