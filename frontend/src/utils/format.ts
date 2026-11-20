/**
 * Formatting helpers. The backend sends raw EUR numbers and ISO dates – format ONLY here (API rule #4/#5).
 * Money uses de-DE as required by docs/API.md ("93.000 €"); UI copy is English.
 */
const eurFmt = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const eurFmtCents = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", minimumFractionDigits: 2 });
const numFmt = new Intl.NumberFormat("de-DE");
const pctFmt = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 1 });

/** 93000 → "93.000 €" */
export const eur = (n: number | null | undefined) => (n == null ? "–" : eurFmt.format(n));
/** 5.21 → "5,21 €" */
export const eurCents = (n: number | null | undefined) => (n == null ? "–" : eurFmtCents.format(n));
/** 1470 → "+1.470 €" (sign always shown) */
export const eurSigned = (n: number) => (n > 0 ? "+" : "") + eurFmt.format(n);
export const num = (n: number) => numFmt.format(n);
/** 15 → "+15 %" */
export const pct = (n: number, signed = true) => `${signed && n > 0 ? "+" : ""}${pctFmt.format(n)} %`;

// ISO "YYYY-MM-DD" must be parsed as a LOCAL date, otherwise it shifts by the timezone offset.
const parseIso = (iso: string) => {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
};

/** "2027-02-03" → "3 Feb 2027" */
export const fmtDate = (iso: string | null | undefined) =>
  iso ? parseIso(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "–";

/** "2027-02-03" → "3 Feb" */
export const fmtDayMonth = (iso: string | null | undefined) =>
  iso ? parseIso(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : "–";

/** ISO datetime → "20 Nov 2026, 14:05" (local time) */
export const fmtDateTime = (iso: string | null | undefined) =>
  iso
    ? new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })
    : "–";
