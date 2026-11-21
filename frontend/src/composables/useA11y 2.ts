import { computed, reactive, ref, watch } from "vue";

/**
 * Accessibility preferences (menu in the top bar). Module-level → shared by every caller.
 * Each setting is an attribute on <html>, styled in styles/tokens.css + main.css:
 *   data-text="lg|xl|xxl"  → root font-size 112.5 / 125 / 137.5 % (every size in the app is rem-based)
 *   data-contrast="high"   → stronger text, borders and tints (light + dark)
 *   data-motion="reduce"   → transitions/animations off
 *   data-links="underline" → every link underlined
 *   data-spacing="wide"    → more letter/word/line spacing
 * Saved in localStorage under KEY; index.html applies the same attributes before first paint (no flash).
 */
export type TextSize = "base" | "lg" | "xl" | "xxl";
export type Contrast = "standard" | "high";

export const TEXT_SIZES: { value: TextSize; pct: number; label: string }[] = [
  { value: "base", pct: 100, label: "Normal text" },
  { value: "lg", pct: 112.5, label: "Large text" },
  { value: "xl", pct: 125, label: "Larger text" },
  { value: "xxl", pct: 137.5, label: "Largest text" },
];

interface Prefs {
  text: TextSize;
  contrast: Contrast;
  /** null = follow the device setting */
  motion: "reduce" | "full" | null;
  links: boolean;
  spacing: boolean;
}

const KEY = "avida-a11y"; // also read by the inline script in index.html
const DEFAULTS: Prefs = { text: "base", contrast: "standard", motion: null, links: false, spacing: false };

function read(): Prefs {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? "{}") as Partial<Prefs>;
    return {
      text: TEXT_SIZES.some((t) => t.value === raw.text) ? (raw.text as TextSize) : DEFAULTS.text,
      contrast: raw.contrast === "high" ? "high" : "standard",
      motion: raw.motion === "reduce" || raw.motion === "full" ? raw.motion : null,
      links: raw.links === true,
      spacing: raw.spacing === true,
    };
  } catch {
    return { ...DEFAULTS };
  }
}

const prefs = reactive<Prefs>(read());

const media = typeof window !== "undefined" ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
const systemReduce = ref(media?.matches ?? false);
media?.addEventListener("change", (e) => (systemReduce.value = e.matches));

function setAttr(name: string, value: string | null) {
  const root = document.documentElement;
  if (value === null) root.removeAttribute(`data-${name}`);
  else root.setAttribute(`data-${name}`, value);
}

function apply(p: Prefs) {
  setAttr("text", p.text === "base" ? null : p.text);
  setAttr("contrast", p.contrast === "high" ? "high" : null);
  setAttr("motion", p.motion);
  setAttr("links", p.links ? "underline" : null);
  setAttr("spacing", p.spacing ? "wide" : null);
  try {
    const isDefault = (Object.keys(DEFAULTS) as (keyof Prefs)[]).every((k) => p[k] === DEFAULTS[k]);
    if (isDefault) localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, JSON.stringify(p));
  } catch {
    /* storage unavailable – settings still apply for this session */
  }
}

if (typeof document !== "undefined") {
  apply(prefs);
  watch(prefs, (p) => apply(p), { deep: true });
}

export function useA11y() {
  /** What the user actually gets: explicit choice, else the device setting. */
  const reduceMotion = computed(() => (prefs.motion === null ? systemReduce.value : prefs.motion === "reduce"));
  const isDefault = computed(() => (Object.keys(DEFAULTS) as (keyof Prefs)[]).every((k) => prefs[k] === DEFAULTS[k]));

  const setReduceMotion = (on: boolean) => {
    // back to "follow the device" when the choice equals the device setting
    prefs.motion = on === systemReduce.value ? null : on ? "reduce" : "full";
  };
  const reset = () => Object.assign(prefs, DEFAULTS);

  return { prefs, reduceMotion, isDefault, setReduceMotion, reset };
}
