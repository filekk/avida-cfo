import { intlLocale, t } from "@/i18n";

/**
 * Formatting helpers. The backend sends raw EUR numbers and ISO dates – format ONLY here (API rule #4/#5).
 * Money uses de-DE in every language as required by docs/API.md ("93.000 €").
 * Dates follow the chosen language (en-GB "3 Feb 2027" · de-DE "3. Feb. 2027") – reactive, so call these in
 * templates/computed and they update on a language switch.
 */
const eurFmt = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const eurFmtCents = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", minimumFractionDigits: 2 });
const numFmt = new Intl.NumberFormat("de-DE");
const pctFmt = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 1 });

/** de-DE prints a hyphen ("-27.882 €"); typeset numbers use the real minus sign U+2212 ("−27.882 €"). */
const minus = (s: string) => s.replace("-", "−");

/** 93000 → "93.000 €" · -27882 → "−27.882 €" */
// `n || 0` turns -0 (e.g. an axis tick computed from a negative range) into 0 → never "-0 €"
export const eur = (n: number | null | undefined) => (n == null ? "–" : minus(eurFmt.format(n || 0)));
/** 5.21 → "5,21 €" */
export const eurCents = (n: number | null | undefined) => (n == null ? "–" : minus(eurFmtCents.format(n || 0)));
/** 1470 → "+1.470 €" (sign always shown) */
export const eurSigned = (n: number) => (n > 0 ? "+" : "") + minus(eurFmt.format(n));
export const num = (n: number) => minus(numFmt.format(n));
/** 1385 → "1,4 KB" · 2_400_000 → "2,3 MB" (1 KB = 1024 bytes; de-DE decimal comma like all numbers) */
export const fmtBytes = (n: number | null | undefined) => {
  if (n == null) return "–";
  if (n < 1024) return `${numFmt.format(n)} B`;
  const kb = n / 1024;
  if (kb < 1024) return `${pctFmt.format(kb)} KB`;
  return `${pctFmt.format(kb / 1024)} MB`;
};
/** 15 → "+15 %" */
export const pct = (n: number, signed = true) => `${signed && n > 0 ? "+" : ""}${minus(pctFmt.format(n))} %`;

// ISO "YYYY-MM-DD" must be parsed as a LOCAL date, otherwise it shifts by the timezone offset.
const parseIso = (iso: string) => {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
};

/** "2027-02-03" → "3 Feb 2027" / "3. Feb. 2027" */
export const fmtDate = (iso: string | null | undefined) =>
  iso ? parseIso(iso).toLocaleDateString(intlLocale.value, { day: "numeric", month: "short", year: "numeric" }) : "–";

/** "2027-02-03" → "3 Feb" / "3. Feb." */
export const fmtDayMonth = (iso: string | null | undefined) =>
  iso ? parseIso(iso).toLocaleDateString(intlLocale.value, { day: "numeric", month: "short" }) : "–";

/**
 * "When was that?" in plain words, getting coarser with age:
 *   < 1 min "just now" · < 1 h "5 minutes ago" · < 1 day "2 hours ago" · < 7 days "yesterday" / "3 days ago"
 *   · older: the date. German via Intl ("vor 5 Minuten", "gestern"). `now` is passed in so callers can tick.
 */
export function fmtAgo(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return "–";
  const then = new Date(iso);
  const s = Math.max(0, (now - then.getTime()) / 1000);
  const rtf = new Intl.RelativeTimeFormat(intlLocale.value, { numeric: "auto" });
  if (s < 60) return t("just now");
  if (s < 3600) return rtf.format(-Math.floor(s / 60), "minute");
  if (s < 86400) return rtf.format(-Math.floor(s / 3600), "hour");
  const day = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((day(new Date(now)) - day(then)) / 86400000);
  return days < 7 ? rtf.format(-days, "day") : then.toLocaleDateString(intlLocale.value, { day: "numeric", month: "short", year: "numeric" });
}

/** "2027-02-03" → "3 February" / "3. Februar" (for sentences) */
export const fmtDayMonthLong = (iso: string | null | undefined) =>
  iso ? parseIso(iso).toLocaleDateString(intlLocale.value, { day: "numeric", month: "long" }) : "–";

/** ISO datetime → "20 Nov 2026, 14:05" / "20. Nov. 2026, 14:05" (local time) */
export const fmtDateTime = (iso: string | null | undefined) =>
  iso
    ? new Date(iso).toLocaleString(intlLocale.value, {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "–";
