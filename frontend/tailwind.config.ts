import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  safelist: [
    'bg-emerald-100', 'text-emerald-700',
    'bg-green-100', 'text-green-700',
    'bg-yellow-100', 'text-yellow-700',
    'bg-orange-100', 'text-orange-700',
    'bg-red-100', 'text-red-600',
    'bg-red-200', 'text-red-700',
    'ring-1', 'ring-blue-400', 'ring-orange-400',
    'bg-orange-50', 'ring-orange-500',
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
      },
    },
  },
  plugins: [],
};
export default config;
