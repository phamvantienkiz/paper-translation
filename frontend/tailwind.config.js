/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        academic: {
          navy: "#1E3A5F",
          "navy-dark": "#14273E",
          "navy-light": "#2B4C77",
          gold: "#B45309",
          "gold-hover": "#92400E",
          "gold-light": "#FEF3C7",
        },
        brand: {
          50: "#f0f6ff",
          100: "#e0edfe",
          200: "#bae0fd",
          500: "#1E3A5F",
          600: "#14273E",
          700: "#0e1a2b",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
        serif: ["'Crimson Pro'", "Georgia", "Cambria", "Times New Roman", "serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      boxShadow: {
        paper: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 20px 25px -5px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(0, 0, 0, 0.05)",
        "paper-hover": "0 10px 15px -3px rgba(0, 0, 0, 0.15), 0 25px 35px -5px rgba(0, 0, 0, 0.18), 0 0 0 1px rgba(0, 0, 0, 0.08)",
      },
    },
  },
  plugins: [],
}
