# QAZen Web UI

Production React SPA for the QAZen human-review surface (Dashboard, Runs, H1–H5 Review, Reports, Settings).

**Stack:** React 19 + TypeScript + Vite + Tailwind CSS 4 + React Router.

**Data:** Talks only to Review API (`:8001`). Mutations are proxied to Orchestrator (`:8002`). Never call Orchestrator or LLM Gateway from the browser.

## Prerequisites

- Node.js 20+
- Review API running on `http://localhost:8001` (and usually Orchestrator + Postgres via `infra/docker compose`)

## Develop (hot reload)

```powershell
cd web
npm install
npm run dev
```

Vite serves at `http://localhost:5173/ui/` and proxies API routes (`/runs`, `/dashboard`, `/reviews`, …) to Review API `:8001`.

## Build (serve from Review API)

```powershell
cd web
npm run build
```

Output lands in `review-api/static/` (Vite `base: /ui/`). Restart or keep Review API running, then open:

`http://localhost:8001/ui/`

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Vite dev server + API proxy |
| `npm run build` | Typecheck + production build → `review-api/static` |
| `npm run preview` | Preview the production build locally |
| `npm test` | Vitest (incl. `runState` mapping tests) |

## Local full stack (reminder)

```powershell
cd infra; docker compose up -d
# LLM Gateway :8000, Orchestrator :8002, Review API :8001 — see repo root README
cd web; npm run build   # after UI changes
```

## Honesty / scope (v1)

- CI/CD and Jenkins: **Mock / Not Configured** unless env says otherwise — no production push UI
- Knowledge Base: **read-only** (no Add/Edit/Delete)
- Reports: **current-run S9 only**; no fake flaky-history trends
- Playwright: Test runner, **not MCP**
- Stop Run / Cancel: not available until Orchestrator exposes it
- Share: copy run URL only

## Contract

API shapes: [`docs/ui-api-contract.md`](../docs/ui-api-contract.md)  
Canonical run/state mapping: [`src/lib/runState.ts`](src/lib/runState.ts)
