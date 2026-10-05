/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  // Theme (colors, fonts, shadows) is defined in src/styles/globals.css @theme block
  // to align with Tailwind CSS v4 conventions.
  theme: {},
  plugins: [],
};