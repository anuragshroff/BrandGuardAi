import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#060B14",
        panel: "#0B1424",
        panelAlt: "#101C31",
        edge: "#1E2C44",
        signal: "#2F6BFF",
        spark: "#F5B700",
        critical: "#FF6B6B",
        warning: "#F5B700",
        info: "#63A4FF",
        success: "#3DDC97",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(47,107,255,0.25), 0 12px 40px -12px rgba(47,107,255,0.45)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.25s ease-out both",
        "pulse-soft": "pulseSoft 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
