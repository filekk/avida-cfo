import type { IconName } from "@/components/ui/icons";
import { t, tn } from "@/i18n";
import type { UploadedContract } from "@/types/api";
import { eur, fmtDate, pct } from "@/utils/format";

/**
 * Shared helpers for the contracts page (upload summary). The file explorer itself: files.ts.
 * Labels stay English here and are translated where they are rendered (never call t() at module level).
 */
type Party = { supplier?: string; customer?: string };
export type ContractRole = "supplier" | "customer";

export const roleOf = (c: Party): ContractRole => (c.customer ? "customer" : "supplier");
export const partyOf = (c: Party) => c.supplier ?? c.customer ?? "–";

export const ROLE: Record<ContractRole, { label: string; icon: IconName }> = {
  supplier: { label: "Supplier", icon: "truck" },
  customer: { label: "Customer", icon: "building" },
};

/**
 * The terms the model read from an uploaded contract – only the ones it actually found, so the owner can
 * compare them with the paper before trusting them. Call at render time (translates and formats).
 */
export function keyTerms(c: UploadedContract): { label: string; value: string }[] {
  const days = (n: number) => tn(n, "{n} day", "{n} days");
  const rows: [string, string | null][] =
    roleOf(c) === "supplier"
      ? [
          ["Monthly fee", c.monthly_fee != null ? eur(c.monthly_fee) : null],
          ["Fixed price until", c.fixed_price_until ? fmtDate(c.fixed_price_until) : null],
          ["Notice before a price change", c.price_change_notice_days != null ? days(c.price_change_notice_days) : null],
          ["Max. price rise per year", c.max_annual_increase_pct != null ? pct(c.max_annual_increase_pct, false) : null],
        ]
      : [
          ["Payment terms", c.payment_terms_days != null ? days(c.payment_terms_days) : null],
          [
            "Changes only in writing",
            c.changes_require_written_agreement != null ? t(c.changes_require_written_agreement ? "Yes" : "No") : null,
          ],
        ];
  return rows.filter((r): r is [string, string] => r[1] !== null).map(([label, value]) => ({ label: t(label), value }));
}
