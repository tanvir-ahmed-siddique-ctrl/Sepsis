/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: "#0B1422",
          800: "#142538",
          700: "#1B2733",
        },
        canvas: "#F7F9FA",
        surface: "#FFFFFF",
        muted: {
          DEFAULT: "#63717D",
          surface: "#F1F4F6",
        },
        ink: "#17232D",
        teal: {
          // #287A88 keeps 4.9:1 contrast on white for text; #4FA8B7 is decorative only.
          DEFAULT: "#287A88",
          dark: "#1F6370",
          light: "#4FA8B7",
          soft: "#DCE8ED",
        },
        border: "#E3E8EC",
        // Compatibility aliases used across existing screens
        mist: "#F7F9FA",
        paper: "#F7F9FA",
        warm: "#FFFFFF",
        forest: "#287A88",
        olive: "#63717D",
        copper: "#8A6A4A",
        clinical: {
          critical: "#B42318",
          high: "#C4500A",
          moderate: "#A15C07",
          low: "#1F7A4D",
          unavailable: "#667085",
        },
        slate: {
          DEFAULT: "#63717D",
          panel: "#F1F4F6",
        },
        risk: {
          stable: "#1F7A4D",
          watch: "#A15C07",
          high: "#B42318",
          insufficient: "#667085",
        },
        accent: "#287A88",
      },
      fontFamily: {
        display: ["var(--font-display)", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["var(--font-display)", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      maxWidth: {
        content: "80rem",
        public: "76rem",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(11, 20, 34, 0.04)",
        card: "0 1px 2px rgba(11, 20, 34, 0.04), 0 8px 24px -12px rgba(11, 20, 34, 0.10)",
        lift: "0 2px 4px rgba(11, 20, 34, 0.04), 0 18px 40px -18px rgba(11, 20, 34, 0.22)",
      },
    },
  },
  plugins: [],
};
