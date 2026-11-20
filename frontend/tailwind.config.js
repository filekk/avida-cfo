/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,vue}"],
  theme: {
    extend: {
      fontSize: { base: ["17px", "1.6"] }, // larger default text – readable for every generation
    },
  },
  plugins: [],
};
