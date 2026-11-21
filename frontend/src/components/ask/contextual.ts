import type { DecisionItem } from "@/components/actions/decision";
import { describeFinding } from "@/components/findings/describe";
import { t } from "@/i18n";
import type { AskSuggestion } from "@/types/api";

/**
 * "Ask your CFO" inside one decision: questions that fit THIS case.
 *   1. the backend's own suggestions that name this supplier / customer (or the overdraft) – sent unchanged, so the
 *      backend recognises them and answers instantly with a prepared answer (`source: "rules"`)
 *   2. topped up with questions written for the case – these are answered by the model like a typed question
 * Max. 4 chips. Texts are translated here → call at render time (computed).
 */
export const MAX_CONTEXT_SUGGESTIONS = 4;

/** Short subject the backend gets in front of a TYPED question ("CloudHost GmbH, price change"), so "is this fair?" works. */
export function contextSubject(item: DecisionItem): string {
  const { action: a, finding: f } = item;
  if (f) {
    const party = describeFinding(f).party;
    return f.kind === "payment_delay"
      ? t("{supplier}: late payment", { supplier: party })
      : t("{supplier}: price change", { supplier: party });
  }
  if (a?.type === "credit_application") return t("Overdraft");
  return a?.title ?? "";
}

export function contextualSuggestions(item: DecisionItem, backend: AskSuggestion[]): AskSuggestion[] {
  const { action: a, finding: f } = item;
  const out: AskSuggestion[] = [];

  // 1 · backend suggestions about this case (instant answers)
  if (f) {
    const { party, shortParty } = describeFinding(f);
    const names = [party, shortParty].filter((n) => n.length > 2).map((n) => n.toLowerCase());
    out.push(...backend.filter((s) => names.some((n) => s.question.toLowerCase().includes(n))));
  } else if (a?.type === "credit_application") {
    out.push(...backend.filter((s) => s.id === "overdraft"));
  }

  // 2 · questions written for the case (answered by the model)
  const own: AskSuggestion[] = [];
  if (f) {
    const party = describeFinding(f).shortParty;
    if (f.kind === "payment_delay") {
      own.push(
        { id: "ctx_delay_balance", agent: "Analyst Agent", question: t("How does the late payment from {party} affect my balance?", { party }) },
        { id: "ctx_delay_interest", agent: "Legal Agent", question: t("Can I charge {party} interest for paying late?", { party }) },
      );
    } else if (f.contract.verdict === "violates") {
      own.push(
        { id: "ctx_pay_anyway", agent: "Analyst Agent", question: t("What does it cost me if I just pay the new {party} price?", { party }) },
        { id: "ctx_reply", agent: "Negotiator Agent", question: t("What happens if {party} refuses my reply?", { party }) },
      );
    } else if (f.contract.verdict === "allowed") {
      own.push(
        { id: "ctx_allowed", agent: "Legal Agent", question: t("Why is the {party} increase allowed?", { party }) },
        { id: "ctx_alternative", agent: "Negotiator Agent", question: t("Can I still ask {party} for a better price?", { party }) },
      );
    } else {
      own.push({ id: "ctx_unclear", agent: "Legal Agent", question: t("What should I check in the {party} email?", { party }) });
    }
  }
  if (a?.type === "credit_application") {
    own.push(
      { id: "ctx_credit_cost", agent: "Analyst Agent", question: t("How much does the overdraft cost me in total?") },
      { id: "ctx_credit_skip", agent: "Analyst Agent", question: t("What happens if I don't take the overdraft?") },
    );
  }
  own.push({ id: "ctx_forecast", agent: "Analyst Agent", question: t("How does this decision change my cash forecast?") });

  const seen = new Set(out.map((s) => s.id));
  for (const s of own) if (!seen.has(s.id)) out.push(s);
  return out.slice(0, MAX_CONTEXT_SUGGESTIONS);
}
