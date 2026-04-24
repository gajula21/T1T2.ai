/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        background: "#2A2A2A",
        card: "#333333",
        "card-dark": "#2A2A2B",
        "primary-text": "#FFFFFF",
        "secondary-text": "#A3A3A3",
        "border-color": "rgba(255, 255, 255, 0.1)",
        task1: "#2563EB", // Blue for task 1
        task2: "#16A34A", // Green for task 2
        "bar-blue": "#3B82F6",
        "bar-green": "#22C55E",
        "bar-yellow": "#EAB308",
        "bar-purple": "#8B5CF6",
      },
    },
  },
  plugins: [],
};
