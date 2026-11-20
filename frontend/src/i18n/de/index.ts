import a11y from "./a11y";
import actions from "./actions";
import ask from "./ask";
import chart from "./chart";
import common from "./common";
import dashboard from "./dashboard";
import layout from "./layout";
import pages from "./pages";
import sync from "./sync";

/**
 * German strings, keyed by the English source text (see i18n/index.ts).
 * One file per area so several people can translate in parallel without conflicts:
 *   common    – shared labels (autonomy levels, verdicts, agents, navigation, page titles, generic buttons)
 *   layout    – sidebar, top bar, footer, language switch
 *   dashboard – overview: headline, KPIs, findings teaser
 *   chart     – forecast chart, period picker, payments donut
 *   sync      – "Check my inbox" box + progress pop-up, pipeline, agent steps
 *   a11y      – accessibility menu, theme toggle
 *   actions   – Action center, decision tiles/focus, action cards, findings split
 *   pages     – policy, history, not-found
 *   ask       – Ask your CFO, contracts page, Analyst briefing, Legal review of drafts
 * Same English text in two files → keep the same German (later files win on merge).
 */
export const DE: Record<string, string> = {
  ...common,
  ...layout,
  ...dashboard,
  ...chart,
  ...sync,
  ...a11y,
  ...actions,
  ...pages,
  ...ask,
};
