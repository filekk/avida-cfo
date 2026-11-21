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
      // categorical slices (payments donut) – same as the Aurum colours by default, 5 distinct hues in high contrast
      slice: { 1: token("slice-1"), 2: token("slice-2"), 3: token("slice-3"), 4: token("slice-4"), 5: token("slice-5") },
    },
    fontFamily: {
      display: ['"Plus Jakarta Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
      sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      mono: ['"JetBrains Mono"', "ui-monospace", "Consolas", "monospace"],
    },
    extend: {
      /*
       * Type scale – the ONLY font sizes to use (no `text-[0.7rem]` one-offs). rem-based on purpose:
       * the accessibility menu scales <html> font-size and everything follows.
       * caption 13px = the floor (pills, badges, axis labels, eyebrows) · label 14px = secondary text.
       */
      fontSize: {
        xs: ["0.8125rem", { lineHeight: "1.35" }], // safety net: never below 13px
        caption: ["0.8125rem", { lineHeight: "1.35" }],
        label: ["0.875rem", { lineHeight: "1.4" }],
        body: ["1rem", { lineHeight: "1.6" }],
        kpi: ["1.625rem", { lineHeight: "1.15", letterSpacing: "-0.015em" }],
      },
      /*
       * ONE shadow, only for things that really float above the content (top-bar pop-ups, tooltips, the chat
       * panel + bubble). Cards and buttons have none: depth = white card on the light page + a 1px line.
       */
      boxShadow: {
        pop: "0 12px 32px -12px rgb(14 42 71 / 0.22)",
      },
      letterSpacing: { eyebrow: ".1em" },
      /* Motion tokens – same curve & speeds everywhere (mirrored as CSS vars in main.css). */
      transitionTimingFunction: {
        DEFAULT: "cubic-bezier(0.22, 1, 0.36, 1)",
        out: "cubic-bezier(0.22, 1, 0.36, 1)",
        "in-out": "cubic-bezier(0.65, 0, 0.35, 1)",
      },
      transitionDuration: { DEFAULT: "200ms", fast: "150ms", base: "250ms", slow: "400ms" },
      keyframes: {
        rise: { from: { opacity: "0", transform: "translateY(6px)" }, to: { opacity: "1", transform: "none" } },
      },
      animation: { rise: "rise 400ms cubic-bezier(0.22, 1, 0.36, 1) both" },
    },
  },
  plugins: [],
};
