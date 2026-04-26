/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0a0c12',
          surface: '#0f1419',
          border: '#2d3748',
        },
      },
    },
  },
  plugins: [],
}
