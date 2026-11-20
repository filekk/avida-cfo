/**
 * Avida CFO – Tailwind theme built on the "Aurum" design tokens (see ProjektPrototyp + src/styles/tokens.css).
 *
 * The default colour palette is REPLACED on purpose: only semantic tokens exist, so `bg-slate-100`
 * & co. do not compile. Every token is an RGB-channel CSS variable → opacity modifiers work
 * (`bg-sun/20`) and dark mode is a pure variable swap (no `dark:` variants needed for colours).
 *
 * @type {import('tailwindcss').Config}
 */
const token = (name) => `rgb(var(--c-${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,vue}"],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    colors: {
      transparent: "transparent",
      current: "currentColor",
      inherit: "inherit",
      white: "#FFFFFF",

      // surfaces (≈60%)
      bg: token("bg"),
      surface: token("surface"),
      line: token("line"),
      input: token("input"),
      grid: token("grid"),

      // structure: navy text + steel secondary text (≈30%)
      fg: token("fg"),
      muted: token("muted"),
      side: { DEFAULT: token("side"), fg: token("side-fg") },

      // accent: sun = the ONE most important thing on screen (≈7–10%)
      sun: { DEFAULT: token("sun"), hover: token("sun-hover"), on: token("on-sun") },
      gold: token("gold"), // sun as text/link on light backgrounds

      // supporting blues
      sky: token("sky"), // chart bars, selection
      mist: { DEFAULT: token("mist"), fg: token("mist-fg") }, // section bg, info chips

      // money semantics only (≈3%)
      mint: token("mint"), // profit / growth in charts
      positive: { DEFAULT: token("positive"), soft: token("positive-soft") },
      negative: { DEFAULT: token("negative"), soft: token("negative-soft") },
      warn: { DEFAULT: token("warn"), soft: token("warn-soft") },

      chart: { line: token("chart-line"), alt: token("chart-alt") },
    },
    fontFamily: {
      display: ['"Plus Jakarta Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
      sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      mono: ['"JetBrains Mono"', "ui-monospace", "Consolas", "monospace"],
    },
    extend: {
      boxShadow: {
        card: "0 1px 2px 0 rgb(14 42 71 / 0.04)",
        float: "0 24px 60px -30px rgb(14 42 71 / 0.35)",
      },
      letterSpacing: { eyebrow: ".12em" },
    },
  },
  plugins: [],
};
