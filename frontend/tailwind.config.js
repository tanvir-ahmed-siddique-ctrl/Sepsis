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
        canvas: "#FAFBF9",
        surface: "#FFFFFF",
        muted: {
          DEFAULT: "#4F5C68",
          surface: "#EEF5F3",
        },
        ink: "#121C26",
        teal: {
          // #287A88 keeps 4.9:1 contrast on white for text; #4FA8B7 is decorative only.
          DEFAULT: "#287A88",
          dark: "#1F6370",
          light: "#4FA8B7",
          soft: "#DCE8ED",
        },
        border: "#D5DDE3",
        // Compatibility aliases used across existing screens
        mist: "#EEF5F3",
        paper: "#FAFBF9",
        warm: "#FFFFFF",
        forest: "#287A88",
        olive: "#4F5C68",
        copper: "#8A6A4A",
        clinical: {
          critical: "#B42318",
          high: "#C4500A",
          moderate: "#A15C07",
          low: "#1F7A4D",
          unavailable: "#667085",
        },
        slate: {
          DEFAULT: "#4F5C68",
          panel: "#EEF5F3",
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
        soft: "0 1px 2px rgba(11, 20, 34, 0.06), 0 2px 8px rgba(11, 20, 34, 0.06)",
        card: "0 1px 3px rgba(11, 20, 34, 0.08), 0 10px 28px -14px rgba(11, 20, 34, 0.18)",
        lift: "0 4px 12px rgba(11, 20, 34, 0.08), 0 20px 44px -18px rgba(11, 20, 34, 0.28)",
        control: "0 1px 2px rgba(11, 20, 34, 0.08), 0 4px 12px -4px rgba(11, 20, 34, 0.14)",
      },
    },
  },
  plugins: [],
};
