import { t } from "@/i18n";
import type { Forecast } from "@/types/api";
import { eur, fmtDayMonthLong } from "@/utils/format";

/**
 * The headline sentence in the UI language, built from the SAME forecast fields the backend uses
 * (backend/app/agents/liquidity.py → headline(): deterministic, no LLM – so this is formatting, not computing).
 * Used only while the backend can't write it in that language yet (Dashboard.lang ≠ UI language).
 * Covers the overdrawn case from backend-dev (min_balance < 0).
 */
export function localHeadline(f: Forecast): string {
  if (!f.first_breach_date) {
    return t("You're safe for the next {n} days. Your balance stays above your safety cushion.", { n: f.horizon_days });
  }
  const params = {
    n: f.days_safe,
    date: fmtDayMonthLong(f.first_breach_date),
    min: eur(f.min_balance),
    abs: eur(Math.abs(f.min_balance)),
    minDate: fmtDayMonthLong(f.min_date),
    buffer: eur(f.buffer),
  };
  return f.min_balance < 0
    ? t(
        "You're safe for the next {n} days. From {date} your balance falls below your safety cushion, and on {minDate} your account would be {abs} overdrawn.",
        params,
      )
    : t("You're safe for the next {n} days. Around {date} your balance drops to {min} – below your safety cushion of {buffer}.", params);
}
