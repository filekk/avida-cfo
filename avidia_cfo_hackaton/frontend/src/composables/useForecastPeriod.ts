import { ref, watch } from "vue";
import { t, tn } from "@/i18n";

/**
 * How far ahead the owner wants to look (chart + payments). Module-level → shared by every caller and
 * kept while navigating; remembered in localStorage.
 *
 * The backend computes ONE forecast of `horizon_days` (env FORECAST_DAYS, 90 by default). The UI only
 * *shows a window* of it – it never invents numbers. Periods longer than the horizon are offered but
 * disabled until the backend runs a longer forecast (FORECAST_DAYS=365 → "Year" lights up by itself).
 */
export interface PeriodPreset {
  days: number;
  /** English – translate where it is shown: t(p.label) */
  label: string;
}
export const PERIOD_PRESETS: PeriodPreset[] = [
  { days: 7, label: "Week" },
  { days: 30, label: "Month" },
  { days: 90, label: "3 months" },
  { days: 365, label: "Year" },
];
export const MIN_PERIOD_DAYS = 3;
const DEFAULT_DAYS = 90;
const KEY = "avida-period";

const read = (): number => {
  try {
    const n = Number(localStorage.getItem(KEY));
    return Number.isInteger(n) && n >= MIN_PERIOD_DAYS ? n : DEFAULT_DAYS;
  } catch {
    return DEFAULT_DAYS;
  }
};

const days = ref(read());
watch(days, (v) => {
  try {
    localStorage.setItem(KEY, String(v));
  } catch {
    /* storage unavailable – still works for this session */
  }
});

/**
 * "7 days" · "30 days" · "12 months" … for titles like "Your money, next …" – translated on every call
 * (t reads the reactive locale), so titles follow a language switch.
 */
export const periodLabel = (d: number) => (d === 365 ? t("12 months") : tn(d, "{n} day", "{n} days"));

export function useForecastPeriod() {
  return { days };
}
