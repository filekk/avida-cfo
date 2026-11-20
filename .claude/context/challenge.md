# Challenge summary — "Autonomous CFO" (Red Hat × Commerzbank, Collabothon 2026)

Source PDFs: `../Materialy/` (Challenge Card, Red Hat technical deck, OpenShift AI Survival Guide, Project Card).

## Business part (Commerzbank)

- **Context:** SME owners often run the finances themselves. Without a CFO this takes time away from the business,
  and important details get overlooked.
- **Goal:** an AI CFO assistant that *monitors financial information, identifies potential issues and proposes
  explainable next steps*, with approval-dependent actions demonstrated in a **simulated** environment.
- **Distinguish clearly** (we map these 1:1 to the autonomy badges):
  1. what agents analyse on their own → `analyzed`
  2. what they recommend → `recommendation`
  3. what needs the user's approval → `approval`
  4. whether execution is simulated or allowed → `simulated`
- **Use case (at least one, end-to-end):** we chose the **Liquidity agent**: monitor accounts, forecast cash flow
  x days ahead, propose credit facilities automatically. (Optional ones not chosen: FX hedging, tax, investment.)
- **Theme "Innovations for all generations":** owners with any level of tech confidence must understand the
  output and stay in control. The app should be "fun and easy to use".
- **Judges expect:** an end-to-end use case, the business logic behind the agent's output explained, and a clear
  view of how the owner understands and responds to the proposed action.

## Technical part (Red Hat)

- **Hard criteria (no points without them):** (1) the app runs on the provided **OpenShift AI** cluster;
  (2) a model deployed on OpenShift AI is used by the app (open-source/open-weights: Granite, Qwen, Mistral…).
- **Soft criteria:** use-case implementation + **UI/UX**.
- **Bonus (focus on 2–4 max, lower weight this year):** vLLM (done), llm-d, MaaS model gateway,
  ogx + MCP, OpenShell / NeMo guardrails, MLflow tracing, Jupyter on OpenShift AI (done, `notebooks/`),
  Dev Spaces (done, `.devfile.yaml`), OSS AI code assistant in Dev Spaces/Jupyter, Quarkus + LangChain4J.
- Cluster: single node, 32 CPU / 128 GB RAM. Enabling everything will crash it.
- Proprietary coding assistants (Claude Code etc.) are allowed.

## Submission (Project Card)

Project name, a one-line summary (≤ 200 chars), tech stack, overview (problem, solution, working prototype,
behind the build, challenges, results & next steps), and the repository URL.

## What this means for the front-end

- The **autonomy level is visible everywhere** an agent did or proposes something.
- **Explainability on screen:** email ↔ contract clause (quote + page) ↔ calculation ("Show calculation").
- **Control:** an editable draft, Approve / Not now, a "simulated" label on every execution, plus the policy and history pages.
- **Honesty:** "cached answer" (`SourceTag`) when the backend used a fallback. (The topbar "AI online" pill was
  removed on 2026-11-20 at the owner's request – too technical for the target user.)
- **For every generation:** one headline sentence, large buttons, plain words, good contrast, mobile, dark mode.
