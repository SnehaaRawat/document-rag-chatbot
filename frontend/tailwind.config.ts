import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FAFAF7",
        paperdim: "#F1F0EA",
        ink: "#1F2421",
        inkfaint: "#5B635E",
        rule: "#DEDCD2",
        moss: "#3D5A50",
        mosslight: "#E4EBE6",
        clay: "#8B6F47",
      },
      fontFamily: {
        serif: ["var(--font-source-serif)", "Georgia", "serif"],
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
