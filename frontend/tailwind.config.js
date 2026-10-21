/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f1c24",
        mist: "#e8eef2",
        slate: {
          panel: "#f4f7f9",
        },
        risk: {
          stable: "#1f7a4d",
          watch: "#b7791f",
          high: "#b42318",
          insufficient: "#667085",
        },
        accent: "#0e7490",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
