import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./providers/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        app: {
          bg: "#f5f6fa",
          surface: "#ffffff",
          sidebar: "#171923",
          "sidebar-hover": "#272b39",
          primary: "#7652f6",
          "primary-hover": "#6240df",
          "primary-soft": "#f0ebff",
          border: "#e7e9f0",
          ink: "#202333",
          muted: "#6b7280",
        },
        brand: {
          50: "#f0ebff",
          100: "#e4dbfd",
          500: "#7652f6",
          600: "#6240df",
          700: "#5234c4",
        },
      },
      boxShadow: {
        card: "0 1px 2px rgb(16 24 40 / 0.06), 0 8px 24px rgb(16 24 40 / 0.04)",
      },
      borderRadius: {
        card: "16px",
        control: "10px",
      },
    },
  },
  plugins: [],
};

export default config;
