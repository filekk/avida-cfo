---
name: api-endpoint
description: Integrate a backend (FastAPI) endpoint into the Avida CFO front-end — read the backend route, add/adjust TypeScript types in types/api.ts, add a typed function in src/api/, expose it via a store or useAsyncData. Use when the back-end team adds or changes an endpoint, when docs/API.md changes, or when the UI needs data it does not fetch yet.
---

# Integrate a backend endpoint

## 1. Read the real shape (don't guess)

1. `docs/API.md`: the agreed contract.
2. `backend/app/main.py`: route, method, request model (pydantic), what it returns.
3. Follow the return value into `orchestrator.py` / `state.py` / `forecast.py` / `agents/*.py` and list every field,
   noting which are optional or nullable and which only appear after `/api/sync`.
4. If it's available, hit it: local backend `curl http://localhost:8080/api/<path>` (or `/docs` Swagger).
   Don't call mutating endpoints (`sync`, `approve`, `reject`, `reset`) on the **shared live cluster**.

## 2. Types → `frontend/src/types/api.ts`

- Mirror the backend field names exactly (snake_case stays snake_case).
- Optional = `?`, nullable = `| null`. Use unions for enums (`"pending" | "executed"`) and discriminated unions
  when the payload depends on a `type` field.

## 3. API function → `frontend/src/api/<area>.ts`

```ts
import type { Thing } from "@/types/api";
import { http } from "./http";

/** GET /api/things – what it's for. */
export const getThings = (signal?: AbortSignal) => http.get<Thing[]>("/things", signal);

/** POST /api/things/{id}/archive – only from an explicit user click. */
export const archiveThing = (id: string) => http.post<Thing>(`/things/${encodeURIComponent(id)}/archive`);
```

- New file? Re-export it in `api/index.ts`.
- Errors surface as `ApiError` (message from FastAPI `detail`, status code). Let the caller show them.
- Streaming (SSE) → follow `api/sync.ts` (handle both `event: error` with data and a dropped connection).

## 4. Expose it

- Shared or flow state → add state plus an action to the relevant Pinia store (`stores/dashboard.ts` pattern:
  loading/error refs, try/catch, update state from the response and don't recompute on the client).
- Page-local read → `useAsyncData(getThings)` in the view.

## 5. Verify

- `npm --prefix frontend run build` (vue-tsc catches every place affected by a type change).
- Exercise it against a local backend (`frontend-verify` skill).
- If you found a contract mismatch, write it up for the back-end team rather than editing `backend/` from the front-end branch.
