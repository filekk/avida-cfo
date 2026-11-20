---
name: frontend-verify
description: Verify the Avida CFO front-end end-to-end — typecheck + production build, run a local offline backend and the Vite dev server, click through the demo flow in a headless browser (sync → findings → approve → policy/history), check console errors, mobile width and dark mode. Use before handing over front-end changes, or when asked to test, run or check the app.
---

# Verify the front-end

## 1. Static

```bash
npm --prefix frontend run build      # vue-tsc --noEmit && vite build → frontend/dist (assets in dist/assets)
```

## 2. Run locally (never test mutations against the shared live cluster)

Backend in offline mode (fallback answers, no model needed). Use a venv **outside the repo** (e.g. the scratchpad):

```bash
python -m venv <scratch>/venv && <scratch>/venv/Scripts/pip install -r backend/requirements.txt
cd backend && LLM_ENABLED=false TRACE_DELAY_S=0.05 <scratch>/venv/Scripts/python -m uvicorn app.main:app --port 8080
```

PowerShell: `$env:LLM_ENABLED="false"; $env:TRACE_DELAY_S="0.05"` before the command.

Front-end: `npm --prefix frontend run dev` (5173; the proxy defaults to :8080). If 5173 is already taken by the
developer's own Vite from this folder, reuse it. HMR serves the current code.

Check `curl http://localhost:5173/api/health` → `{"status":"ok"}` (proves the proxy works).

## 3. Click through (Playwright, script in the scratchpad, not in the repo)

Minimum scenario:
1. `POST /api/reset`, open `/` → "Money in the bank today" is visible, the headline is shown.
2. Click **Check my inbox** → the trace list grows → the button becomes **Check again** (≤ 90 s).
3. `/findings` → 2 cards → open one → **Show calculation** shows the formula.
4. `/decisions` → **Approve and send** → "sent (simulated…)", and "Saved by Avida" = 17.640 € → **Not now** on the second one.
5. `/policy` → 6 rows. `/history` → entries include "Approved". `/does-not-exist` → 404 page.
6. Theme toggle → `html[data-theme="dark"]`. Wait ~600 ms before screenshots (colour transitions).
7. Viewport 390×844 → `document.documentElement.scrollWidth - innerWidth === 0`, and nothing overflows its card.
8. Collect `console.error` + `pageerror`. The expected result is none.
9. `POST /api/reset` at the end.

Look at the screenshots yourself, judge them against `.claude/rules/design-system.md`, and report what you saw.

## 4. Clean up

Stop the uvicorn and Vite processes **you** started (not the developer's). Leave no test files in the repo.
