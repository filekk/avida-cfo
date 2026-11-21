# Back-end support for the front-end tasks (2026-11-21)

What the back-end now provides for each item of today's front-end list. Design is entirely yours: this
document only says **where the data comes from**. Contract details and full JSON: [API.md](API.md).
TypeScript types are already updated in `frontend/src/types/api.ts` (typecheck passes). The `api/*` functions,
stores and UI are not touched.

Run locally: `cd backend && LLM_ENABLED=false uvicorn app.main:app --port 8080 --reload` (the shared cluster is
updated only after deploy). Swagger: `http://localhost:8080/docs`.

---

## 1. Chart (bottom left) + better chart

| You want | Use |
|---|---|
| Balance line | `scenarios.<name>.series[].balance` (unchanged) |
| Daily in/out bars | `series[].inflow` (≥ 0) and `series[].outflow` (≤ 0), new |
| "Why does it drop here?" markers / tooltips | `scenarios.<name>.events[]`: every payment `{date, amount, label, category, counterparty}` |
| Spending donut / category breakdown | `outflows_by_category[]` / `inflows_by_category[]` `{category, total, count}`, whole horizon. For a shorter window, aggregate `events` yourself |
| Safety cushion line, breach area | `buffer`, `first_breach_date`, `last_breach_date`, `min_date` (unchanged) |
| Compare scenarios | `current` / `if_accepted` / `recommended` (after sync) |

Categories to translate in the UI: `revenue`, `payroll`, `supplier`, `rent`, `loan`, `tax`, `other`.
Payment `label`s come from the bank data and stay English.

## 2. Animations

**Changing numbers.** Everything you need for "from → to":
- after a sync: `Dashboard.kpis_previous` (start screen) → `Dashboard.kpis` (new). `null` before the first sync.
- after approve / reject: `saved_liquidity_previous` → `saved_liquidity` in the response.

**More visible AI-to-AI communication.** SSE `/api/sync` events are richer:
- new `phase` events: 6 stages `inbox → legal → forecast → negotiation → approval → briefing`, each `start` / `done`,
  with `index` / `total` / `label`. Use them for a progress bar / stepper. Listen with `es.addEventListener("phase", …)`;
  old listeners keep working.
- every `trace` now has `id`, `ts`, `elapsed_ms`, `phase`.
- handoffs (`to` + `kind: "handoff"`) are unchanged: agent A → agent B messages.
- `finding_id` + `partner` on every step about one email. During `negotiation` 3 negotiations run **in parallel**
  and interleave. Group by `finding_id` to draw one thread / lane per partner.
- `action_id` on the "Waiting for your approval" steps, so the animation can end on the created card.
- `GET /api/sync/trace` replays the last sync (e.g. after a page reload, or an "replay the agents" button).
- Pacing: the backend waits `TRACE_DELAY_S` (default 0.4 s) between events. Ask us if you want it slower or faster for the demo.

## 3. Agent chat inside every problem, with hints for the decision

One request for the problem view:
```
GET /api/actions/{id}/context?lang=de     → { action, finding, suggestions }
GET /api/findings/{id}/context?lang=de    → also for findings without an action (allowed increases)
```

- **Decision hints without chatting:** `action.decision`
  - `recommended`, `certainty` (`medium` = depends on the partner)
  - `deadline` + `deadline_reason` ("decide before 01.01.2027 – the new price would be invoiced from then")
  - `options[]`: `approve` / `not_now`, each with `label`, `summary` (one sentence) and `effects` (numbers:
    `min_balance`, `cost_12m`, …) for a side-by-side comparison.
- **Compact card text:** `action.why_short` (one line); `why` stays the long version.
- **Chat:** `POST /api/ask` with `action_id` or `finding_id`:
  - chips = `suggestions` of the context (`why`, `cost`, `not_now`, `deadline`, …). Send the chip's `question`
    unchanged and the answer is instant (`source: "rules"`).
  - typed questions take 3–7 s with the model. Send `history` (last turns `{role: "owner"|"agent", text}`) for
    follow-ups. The backend keeps no chat state; the conversation lives in the UI.
  - answers are not streamed (numbers are checked first). Show "thinking…" with the agent's name.
- **Draft editing helpers** (send_email actions):
  - `POST /api/actions/{id}/review {body, lang}`: **instant** check of the edited text (clause cited, amounts, no
    placeholder, no internal finance). Call it debounced while typing and show the issues next to the editor.
  - **Rewrite button** = `POST /api/actions/{id}/redraft {instruction?, body?, lang}`: "make it softer" /
    "mention we are customers since 2019" / "in German" → the Negotiator rewrites and the Legal Agent reviews (3–8 s).
    - `instruction` empty or omitted = plain "write it again".
    - chips + input placeholder: `GET /api/actions/{id}/redraft/hints?lang=` (send the chip's `instruction` unchanged).
    - send the editor's current text as `body` to iterate; `attempt` (1, 2, 3 …) lets you show "Version 2".
    - returns a **proposal**: put it into the editor (keep the previous text for an "undo" if you like); the owner
      still clicks Approve (`edited_body`). Show `note` when the model was unavailable (`changed: false`).
- Rule 1 still holds: none of these endpoints executes anything.

## 4. Imported files page: filters, sorting, upload date

`GET /api/contracts` now returns per file: `party`, `party_type` (supplier / customer), `file_name`, `file_type`
(md / txt / pdf), `size_bytes`, `pages`, `uploaded_at` (null for the prepared index), `extraction_seconds`,
`source`, `warnings_count`, `clauses` (count), `used_in_last_sync`, `used_by_findings`.

- Server-side filter / sort (optional, the list is small): `?q=&origin=index|uploaded&party_type=supplier|customer&sort=-uploaded_at`
  (sort keys: `uploaded_at`, `party`, `title`, `start_date`, `size_bytes`, `pages`, `-` = descending, empty values last).
- Detail view: `GET /api/contracts/{id}`: extracted terms + **all clauses**.
- Preview / download the original: `GET /api/contracts/{id}/file` (inline) or `?download=true`.

## 5. De-slop: less clutter

- Short texts for dense layouts: `action.why_short`, `decision.options[].summary`, `phase.label`.
- Numbers are structured (`effects`, `kpis`, `impact`), so you can show a number instead of a sentence.
- Long texts (`why`, `explanation_simple`, `calculation`, `key_points`) stay available for "details" drawers.

## Languages (CONTRACT_PROPOSALS.md item 1: done)

Send `?lang=de` on `dashboard`, `sync`, `approve` / `reject`, `context`, `policy`, `reset`, and `lang` in the body of
`ask` / `review` / `redraft`. All backend texts come back in German, including headline, steps, action texts,
checks, calculations, briefing and policy.
- One sync serves both languages: after a language switch just re-fetch `GET /api/dashboard?lang=…`.
- Model-written texts exist only in the sync's language (`Dashboard.sync_lang`); in the other language you get
  the rule-based text with `source: "rules"`.
- The front-end's own headline fallback (`headline.ts`) is no longer needed when `Dashboard.lang` matches.
- Not translated: draft emails, original emails, contract quotes, bank-data labels, the model's review remarks.

## Breaking changes

None for existing code: all old fields are still there with the same English values under `?lang=en`.
In `types/api.ts` some new fields are typed as **required** because the backend always sends them
(`why_short`, `decision`, `kpis_previous`, `sync_lang`, `lang`, contract metadata). If you build
mock objects of these types, add those fields.
