/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#020617",
        surface: "#020817",
        primary: {
          50: "#eff6ff",
          500: "#2563eb",
          600: "#1d4ed8"
        },
        danger: {
          500: "#ef4444"
        },
        success: {
          500: "#22c55e"
        },
        warning: {
          500: "#f97316"
        },
        info: {
          500: "#06b6d4"
        }
      },
      boxShadow: {
        card: "0 20px 25px -5px rgba(15,23,42,0.6), 0 8px 10px -6px rgba(15,23,42,0.6)"
      }
    }
  },
  plugins: []
};

