/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#F7F8F6",
        surface: "#FFFFFF",
        muted: {
          DEFAULT: "#64747B",
          surface: "#EEF3F1",
        },
        ink: "#142832",
        teal: {
          DEFAULT: "#087E83",
          dark: "#075F65",
        },
        border: "#DCE5E3",
        // Compatibility aliases used across existing screens
        mist: "#F7F8F6",
        paper: "#F7F8F6",
        warm: "#FFFFFF",
        forest: "#087E83",
        olive: "#6F8480",
        copper: "#8A6A4A",
        clinical: {
          critical: "#B42318",
          high: "#DC6803",
          moderate: "#B7791F",
          low: "#1F7A4D",
          unavailable: "#667085",
        },
        slate: {
          DEFAULT: "#64747B",
          panel: "#EEF3F1",
        },
        risk: {
          stable: "#1F7A4D",
          watch: "#B7791F",
          high: "#B42318",
          insufficient: "#667085",
        },
        accent: "#087E83",
      },
      fontFamily: {
        display: ["var(--font-display)", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      maxWidth: {
        content: "80rem",
        public: "72rem",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(20, 40, 50, 0.04)",
      },
    },
  },
  plugins: [],
};
