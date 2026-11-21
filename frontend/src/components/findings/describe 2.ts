import { t } from "@/i18n";
import type { Finding } from "@/types/api";
import { eur, fmtDate, pct } from "@/utils/format";

/**
 * One finding, in words and numbers, whatever its kind:
 *   price_change with figures  → "+15 %", from 1 Jan 2027, old → new price
 *   payment_delay              → "14 days late", invoice, due → new payment date
 *   no figures in the email    → "No figures", the agents ask for them
 * Every card and the Action center use this, so the three kinds look the same everywhere.
 * Texts are translated here (t() reads the reactive locale) → call it at render time (computed / template).
 */
export interface FindingFacts {
  party: string;
  /** Short party name for tiles ("CloudHost" instead of "CloudHost GmbH"). */
  shortParty: string;
  /** The headline number: "+15 %", "14 days late", "No figures". */
  figure: string;
  /** One line under the headline: date / invoice / why there is no number. */
  sub: string;
  /** Old → new monthly price, only for price changes with figures. */
  priceBar: { from: number; to: number } | null;
  /** Up to three money facts for the footer of the detail. */
  stats: { icon: "euro" | "chart" | "calendar" | "clock"; label: string; value: string }[];
  /** "Extra / year 504 €", "Invoice 18.400 €" – the one number for a tile. */
  key: { label: string; value: string } | null;
}

const LEGAL_FORM = /\s+(GmbH|AG|KG|UG|SE|e\.K\.|OHG|GbR)(?=\s|$).*$/;

export function describeFinding(f: Finding): FindingFacts {
  const x = f.extraction;
  const party = x.party || x.supplier || x.customer || t("Unknown");
  const shortParty = party.replace(LEGAL_FORM, "");

  if (x.figures_stated === false) {
    return {
      party,
      shortParty,
      figure: t("No figures"),
      sub: t("The email announces a change but gives no exact numbers."),
      priceBar: null,
      stats: [],
      key: null,
    };
  }

  if (f.kind === "payment_delay") {
    const late = x.days_late ?? f.impact.days_late;
    return {
      party,
      shortParty,
      figure: late != null ? t("{n} days late", { n: late }) : t("Late payment"),
      sub: t("Invoice {invoice} · due {due} → now {now}", {
        invoice: x.invoice ?? "",
        due: fmtDate(x.due_date),
        now: fmtDate(x.new_payment_date),
      }),
      priceBar: null,
      stats: [
        { icon: "euro", label: t("Invoice amount"), value: eur(x.amount) },
        { icon: "clock", label: t("Days late"), value: late != null ? String(late) : "–" },
        { icon: "chart", label: t("Lowest balance drops by"), value: eur(f.impact.lowest_balance_effect) },
      ],
      key: { label: t("Invoice"), value: eur(x.amount) },
    };
  }

  return {
    party,
    shortParty,
    figure: pct(x.increase_pct ?? 0),
    sub: t("from {date}", { date: fmtDate(x.effective_date) }),
    priceBar: x.old_monthly != null && x.new_monthly != null ? { from: x.old_monthly, to: x.new_monthly } : null,
    stats: [
      { icon: "euro", label: t("Extra per month"), value: eur(f.impact.monthly) },
      { icon: "chart", label: t("Within your forecast"), value: eur(f.impact.in_horizon) },
      { icon: "calendar", label: t("Next 12 months"), value: eur(f.impact.next_12_months) },
    ],
    key: { label: t("Extra / year"), value: eur(f.impact.next_12_months) },
  };
}
