import { computed, ref } from "vue";

export type ThemeChoice = "light" | "dark" | "system";
const KEY = "avida-theme"; // also read by the inline script in index.html (no flash on load)

const read = (): ThemeChoice => {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
};

const choice = ref<ThemeChoice>(read());
const media = typeof window !== "undefined" ? window.matchMedia("(prefers-color-scheme: dark)") : null;
const systemDark = ref(media?.matches ?? false);
media?.addEventListener("change", (e) => (systemDark.value = e.matches));

function apply(t: ThemeChoice) {
  const root = document.documentElement;
  if (t === "system") delete root.dataset.theme;
  else root.dataset.theme = t;
  try {
    if (t === "system") localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, t);
  } catch {
    /* storage unavailable – theme still applies for this session */
  }
}

/** Light/dark theme (Aurum "Noc"). Module-level state → shared by every caller. */
export function useTheme() {
  const isDark = computed(() => (choice.value === "system" ? systemDark.value : choice.value === "dark"));

  function set(t: ThemeChoice) {
    choice.value = t;
    apply(t);
  }
  const toggle = () => set(isDark.value ? "light" : "dark");

  return { choice, isDark, set, toggle };
}
