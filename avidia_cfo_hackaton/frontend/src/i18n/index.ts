import { computed, ref, watch } from "vue";
import { DE } from "./de";

/**
 * Tiny i18n (no dependency). English source text IS the key – gettext style:
 *   {{ t("Check my inbox") }}            → "Posteingang prüfen" in German
 *   t("{n} steps", { n: 12 })            → placeholders in {braces}
 *   tn(n, "{n} step", "{n} steps")       → singular / plural (same rule in EN and DE)
 * German strings live in i18n/de/<area>.ts (one file per area, merged in de/index.ts).
 * A missing German string falls back to English; in dev it is collected in `window.__i18nMissing`.
 *
 * `t` reads the reactive `locale`, so templates and computed() re-render on a language switch.
 * Do NOT call t() at module level (constants) – store the English text and translate where it is shown.
 * Backend text (headline, agent messages, email drafts…) arrives in English and is shown as is.
 */
export type Locale = "en" | "de";

export const LOCALES: { code: Locale; label: string; short: string }[] = [
  { code: "en", label: "English", short: "EN" },
  { code: "de", label: "Deutsch", short: "DE" },
];

const KEY = "avida-lang"; // also read by the inline script in index.html (<html lang> before first paint)

function read(): Locale {
  try {
    const v = localStorage.getItem(KEY);
    if (v === "en" || v === "de") return v;
  } catch {
    /* storage unavailable */
  }
  return "en";
}

export const locale = ref<Locale>(read());

watch(
  locale,
  (l) => {
    if (typeof document !== "undefined") document.documentElement.lang = l;
    try {
      localStorage.setItem(KEY, l);
    } catch {
      /* storage unavailable – still switches for this session */
    }
  },
  { immediate: true },
);

/** Locale for dates and plain numbers. Money stays de-DE in both languages (API rule: "93.000 €"). */
export const intlLocale = computed(() => (locale.value === "de" ? "de-DE" : "en-GB"));

const missing = new Set<string>();
function report(text: string) {
  if (!import.meta.env.DEV || missing.has(text)) return;
  missing.add(text);
  (window as unknown as { __i18nMissing?: string[] }).__i18nMissing = [...missing];
}

export function t(text: string, params?: Record<string, string | number>): string {
  let out = text;
  if (locale.value === "de") {
    const hit = DE[text];
    if (hit !== undefined) out = hit;
    else report(text);
  }
  return params ? out.replace(/\{(\w+)\}/g, (m, k: string) => (k in params ? String(params[k]) : m)) : out;
}

/** Singular/plural: tn(3, "{n} step", "{n} steps") → "3 steps" / "3 Schritte". `{n}` is filled in. */
export const tn = (n: number, one: string, other: string, params?: Record<string, string | number>) =>
  t(n === 1 ? one : other, { n, ...params });

export function setLocale(l: Locale) {
  locale.value = l;
}
