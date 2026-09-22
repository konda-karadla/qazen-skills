# QAZen Browser E2E Test Plan

Executable browser end-to-end coverage of **QAZen itself** (Review SPA + H1–H5 human gates).  
This document is the browser E2E master plan. API, resilience, and domain suites live in related plans (see §16).

---

## 1. Scope & purpose

### In scope

- Review UI at `http://localhost:8001/ui/` (routes in `web/src/App.tsx`)
- Shell navigation, Dashboard, catalogs, New Run, Run Detail, H1–H5 review workspaces
- Two golden paths (all-pass and execution-failure)
- Live state / polling / multi-tab sync
- Gate decision integrity (Approve, Request Changes, Reject)
- Honesty / integration truthfulness
- Responsive and accessibility **smoke** (not a full a11y audit)

### Out of scope (this file)

- API/contract-only suites
- Resilience / chaos injection catalogs
- Domain portfolio scenarios (e-commerce, banking, etc.)
- Playwright suite implementation (document first; automate later)

### Product honesty (v1)

From `web/README.md` — tests must assert the UI does **not** over-claim:

| Area | Current truth |
| --- | --- |
| Knowledge Base | Read-only |
| CI/CD / Jenkins | Mock / not connected unless env says otherwise |
| Reports | Current-run S9 only; no fabricated flaky history |
| Playwright | Test runner, **not** MCP |
| Stop / Cancel run | Not available |
| Share | Copy run URL only |

### Request Changes (current backend truth)

Do **not** assert “terminal `*_changes_requested` / no resume.” That is not how the product works today.

```text
Request Changes
  → review decision = changes_requested
  → current_stage = {gate}_revising, status = running
  → graph revises prior phase
  → new pending review at same gate (artifact_version bumps)
  → run stays alive
```

Reject is the hard-stop: `{gate}_rejected` + `status=failed`.  
Changed requirements that need a different pipeline start: **create a new run** (no selective incremental regeneration).

---

## 2. Preconditions

### 2.1 Services

| Service | Port | Role |
| --- | --- | --- |
| LLM Gateway | `8000` | Skill invoke |
| Review API + UI | `8001` | SPA + read APIs; proxies mutations |
| Orchestrator | `8002` | Pipeline writer |
| Postgres | `5432` | Runs, artifacts, reviews, checkpoints |
| MinIO | `9000` / console `9001` | Evidence objects (optional best-effort) |

Typical start:

```powershell
cd infra; docker compose up -d
.\scripts\start-local-ollama.ps1
# Gateway :8000, Review :8001, Orchestrator :8002
```

### 2.2 UI

- Production: build `web/` → served at `http://localhost:8001/ui/`
- Dev: Vite `http://localhost:5173/ui/` with API proxy to `:8001`
- Browser base URL for this plan: **`http://localhost:8001/ui/`**

### 2.3 LLM / execution modes

State the mode used for each long phase:

| Mode | When |
| --- | --- |
| Live Ollama (`LLM_PROFILE=ollama`) | Manual / local golden paths |
| `LLM_PROVIDER=mock` | Fast / CI-friendly generation |
| `S6_EXECUTION_MODE=playwright` | Real browser suite in GOLDEN-01/02 |
| `S6_EXECUTION_MODE=mock` | Speed; still exercise H4/H5 UI |

### 2.4 Test data

**Default golden requirement:**

> Users must log in with valid credentials and reach the dashboard.

| Field | Default |
| --- | --- |
| Requirement type | User Story |
| Environment | Test |
| Branch | main |
| Reviewer | `qa-lead` |
| Optional | Requirement ID, base URL, labels as needed per case |

**Cleanup:** Prefer leaving completed/failed runs in DB for audit unless the case creates many duplicates — then note run IDs and delete only if a cleanup script/API exists. Do not wipe shared Postgres casually.

---

## 3. Selector strategy

1. **Role + accessible name** (preferred)  
   Example: `getByRole('button', { name: 'Start QA Run' })`
2. **Stable heading / visible text** when role is insufficient
3. **`data-testid` only when necessary** (avoid sprinkling unless automation is blocked)
4. **Poll** run detail / review evidence for stage/gate changes — avoid fixed long sleeps
5. Prefer `http://localhost:8001/ui/...` deep links for seeded-state cases

Observed accessible names (smoke):

| Control | Name / cue |
| --- | --- |
| Nav | Dashboard, New Run, Runs, Reviews, Test Cases, Scripts, Executions, Reports, Knowledge Base, CI/CD, Settings |
| New Run | Start QA Run; Requirement / User Story |
| Review | Approve, Request Changes, Reject; Reviewer; Comments |
| Confirm dialogs | Approve this gate? / Request changes? / Reject this run? |
| Header | Environment; Notifications |

---

## 4. Phase 0 — Environment & smoke

**Goal:** Application shell loads; every primary destination renders its page shell without fatal errors.

### BRW-P0-001 — SPA boot and brand shell

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Review API up; static SPA built |
| Test Data | — |
| Steps | 1. Open `/ui/` 2. Observe shell |
| Expected Result | Title/brand shows **QAZen** and **AI for Better Quality**; sidebar + header present; no blank fatal error |
| Cleanup | — |
| Automation Notes | `getByText('QAZen')`; heading region on dashboard |

### BRW-P0-002 — Primary navigation destinations render

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | BRW-P0-001 pass |
| Test Data | — |
| Steps | Visit each nav destination: `/`, `/runs/new`, `/runs`, `/reviews`, `/test-cases`, `/scripts`, `/executions`, `/reports`, `/knowledge`, `/cicd`, `/settings` |
| Expected Result | Each page loads successfully with expected title/content region and **no fatal error banner that blocks the page shell**. Not merely “URL reachable.” |
| Cleanup | — |
| Automation Notes | Assert page heading per route (e.g. “Start a New QA Run”, “Settings”) |

### BRW-P0-003 — Environment selector and notifications control

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | `/ui/` loaded |
| Test Data | — |
| Steps | Locate Environment combobox and Notifications button |
| Expected Result | Both present and operable (selector changes value; notifications button clickable). Environment is UI-only filter (does not remount services). |
| Cleanup | Reset selector to Test |
| Automation Notes | `getByLabel('Environment')`, `getByRole('button', { name: 'Notifications' })` |

### BRW-P0-004 — Settings honesty indicators

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Integrations status API healthy |
| Test Data | — |
| Steps | Open Settings; read LLM, Playwright, CI/CD, Knowledge, Stop/cancel rows |
| Expected Result | No unsupported capability presented as fully active. Playwright shows MCP: no (or equivalent). Knowledge writable: no. Stop/cancel unavailable. CI mock/not connected labeled honestly. |
| Cleanup | — |
| Automation Notes | Settings headings: “Playwright”, “CI/CD”, “Knowledge Base”, “Security” |

---

## 5. Phase 1 — Dashboard & catalogs

### BRW-P1-001 — Dashboard metrics and empty/populated regions

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Dashboard API available |
| Test Data | Empty DB **or** existing runs |
| Steps | Open Dashboard; observe metric cards and sections Pending Your Review, CI/CD Gate Status, Recent Runs |
| Expected Result | Metrics render (numbers or placeholders). Empty states are explicit (e.g. “No pending reviews”, “No runs yet”). CI mock banner when not connected. No crash. |
| Cleanup | — |
| Automation Notes | Heading “QA Automation Overview”; MetricCard labels Active Runs, Pending Reviews, etc. |

### BRW-P1-002 — Catalog pages load

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | — |
| Test Data | — |
| Steps | Open Runs, Reviews, Test Cases, Scripts, Executions |
| Expected Result | Each shows table **or** empty state; no fatal error |
| Cleanup | — |
| Automation Notes | Table headers when data exists |

### BRW-P1-003 — Pending review count consistency

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | At least one pending H-gate **or** zero pending (both valid) |
| Test Data | Seeded paused run preferred |
| Steps | 1. Note Dashboard “Pending Reviews” metric 2. Note Reviews nav badge (if any) 3. Open Reviews page; count pending items |
| Expected Result | **Dashboard pending count = Reviews nav badge (when shown) = Reviews page pending count** |
| Cleanup | — |
| Automation Notes | Badge only renders when count &gt; 0; treat missing badge as 0 |

---

## 6. Phase 2 — New Run

### BRW-P2-001 — Happy path submit

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Orchestrator + Gateway reachable |
| Test Data | Default golden requirement |
| Steps | New Run → fill requirement → Start QA Run |
| Expected Result | Navigates to `/runs/{run_id}`; run detail loads for that ID |
| Cleanup | Note `run_id` for later phases |
| Automation Notes | `getByRole('button', { name: 'Start QA Run' })` |

### BRW-P2-002 — Empty requirement blocked

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | New Run page |
| Test Data | Cleared requirement text |
| Steps | Clear textarea; attempt submit |
| Expected Result | No navigation; validation/error (“Requirement text is required” or HTML5 required); no new run |
| Cleanup | — |
| Automation Notes | `required` on textarea |

### BRW-P2-003 — Optional metadata passthrough

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Orchestrator up |
| Test Data | REQ id, type BRD, env staging, base URL, branch, labels |
| Steps | Fill optional fields; submit |
| Expected Result | Run created; metadata visible on run detail / stored on run input as applicable |
| Cleanup | Note `run_id` |
| Automation Notes | Labels are comma-separated |

### BRW-P2-004 — Double-submit creates one run

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Orchestrator up |
| Test Data | Unique requirement suffix (timestamp) |
| Steps | Rapid double-click Start QA Run |
| Expected Result | Exactly one run created for the action; button busy/disabled during submit; no duplicate navigations creating two IDs |
| Cleanup | Note `run_id`(s); investigate if two appear |
| Automation Notes | Assert `submitting` disables button |

### BRW-P2-005 — XSS / HTML rendered as text

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Orchestrator up |
| Test Data | Requirement containing `<script>alert(1)</script>` and HTML tags |
| Steps | Create run; open run detail / H1 when available |
| Expected Result | Markup shown as text; script does not execute; no HTML injection into DOM as live nodes |
| Cleanup | Note `run_id` |
| Automation Notes | Check `textContent`, not executed dialogs |

### BRW-P2-006 — Orchestrator / POST /runs failure presentation

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Ability to stop Orchestrator **or** mock 500 on `POST /runs` |
| Test Data | Valid requirement |
| Steps | Submit while Orchestrator down or returning 500 |
| Expected Result | Meaningful error banner/message; stay on New Run; **no** silent success navigation; no duplicate runs on retry after recovery unless user submits again |
| Cleanup | Restart Orchestrator |
| Automation Notes | May use network interception in Playwright |

### BRW-P2-007 — Slow POST /runs and refresh during submission

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Delay injection on `POST /runs` (proxy/mock) |
| Test Data | Valid requirement |
| Steps | A) Submit and wait through slow response B) Submit then refresh mid-flight |
| Expected Result | A) Eventually navigates once or shows error; button not endlessly double-firing. B) No orphan UX claiming success without a run; if run was created server-side, user can find it under Runs |
| Cleanup | Check Runs list for orphans |
| Automation Notes | Network throttle / route delay |

### BRW-P2-008 — Gateway unavailable at start (if surfaced)

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Gateway stopped; Orchestrator may still accept create then fail later |
| Test Data | Valid requirement |
| Steps | Start run; observe UI through first stages |
| Expected Result | Either create fails with clear error **or** run enters failed/error state visible on Run Detail — never a silent hang with no status |
| Cleanup | Restart Gateway |
| Automation Notes | Distinguish create-time vs mid-pipeline failure |

---

## 7. Phase 3 — Run Detail

### BRW-P3-001 — Timeline matches backend state

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Known run with readable `GET /runs/{id}` |
| Test Data | Seeded paused / completed / failed runs |
| Steps | Open `/runs/{runId}`; compare UI status, current stage, pending gate, artifacts, and review decisions to API payload |
| Expected Result | Pipeline timeline and pills derived correctly from `current_stage`, `pending_gate`, artifact presence, and review history (`web/src/lib/runState.ts`) — not hard-coded fiction |
| Cleanup | — |
| Automation Notes | Cross-check API in automation fixture |

### BRW-P3-002 — Major run states render

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | One run per state (or sequential) |
| Test Data | Paused H1–H5, completed, failed/`*_rejected`, `*_revising` if available |
| Steps | Open each run detail |
| Expected Result | Distinct, correct UI status for each state; Open Review CTA when pending gate |
| Cleanup | — |
| Automation Notes | Deep-link each `run_id` |

### BRW-P3-003 — Pipeline node click shows stage context

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Run with multiple artifacts |
| Test Data | Completed or mid-pipeline run |
| Steps | Click each pipeline node; observe artifact/stage context / filters / viewer |
| Expected Result | Corresponding artifact or stage context appears for each node that has data |
| Cleanup | — |
| Automation Notes | `PipelineTimeline` interactions |

### BRW-P3-004 — Share and no Stop/Cancel

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Any run detail |
| Test Data | — |
| Steps | Use Share; search for Stop/Cancel |
| Expected Result | Share copies run URL (or equivalent). **No** Stop/Cancel control that claims to cancel the orchestrator run |
| Cleanup | — |
| Automation Notes | Share2 control; Square/stop must be absent or disabled/honest |

---

## 8. Phase 4 — H1–H5 Review

Gate titles:

| Gate | Title cue |
| --- | --- |
| H1 | H1 — Requirement Review |
| H2 | H2 — Test Case Review |
| H3 | H3 — Script Review |
| H4 | H4 — Execution & Stability Review |
| H5 | H5 — Release Review / Go-No-Go |

### BRW-P4-001 — H1 evidence and decision panel

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Run paused at H1 |
| Test Data | Reviewer `qa-lead` |
| Steps | Open `/runs/{id}/review/H1`; inspect S1/S2 evidence; see Approve / Request Changes / Reject |
| Expected Result | Evidence blocks for normalized requirement and ambiguity; decision panel requires reviewer; confirm dialog before commit |
| Cleanup | Leave pending unless part of golden path |
| Automation Notes | Evidence titles “S1 — Normalized requirement”, “S2 — Ambiguity analysis” |

### BRW-P4-002 — H2 evidence

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Run paused at H2 |
| Test Data | — |
| Steps | Open H2 workspace |
| Expected Result | S3 test cases and S4 test data visible; decision panel operable |
| Cleanup | — |
| Automation Notes | “S3 — Test cases”, “S4 — Test data” |

### BRW-P4-003 — H3 script review (special)

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Run paused at H3 |
| Test Data | — |
| Steps | Open H3; inspect automation model and compiled Playwright source |
| Expected Result | S5 model + Playwright source (or compiled artifact) visible so reviewer can judge assertion quality |
| Cleanup | — |
| Automation Notes | “S5 — Automation model”; “Compiled Playwright” |

### BRW-P4-004 — H4 execution & classification

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Run paused at H4 |
| Test Data | — |
| Steps | Open H4 |
| Expected Result | S6 execution, S7 classification, S8 boundary, S9 report evidence present as available |
| Cleanup | — |
| Automation Notes | GateEvidence H4 blocks |

### BRW-P4-005 — H5 release / go-no-go

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Run paused at H5 |
| Test Data | — |
| Steps | Open H5 |
| Expected Result | S10 release summary factual (no AI go/no-go recommendation inventing pass); decision panel operable |
| Cleanup | — |
| Automation Notes | “S10 — Release summary” |

### BRW-P4-006 — Wrong-gate URL must not allow decision

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Run currently pending at H3 (not H5) |
| Test Data | Same `run_id` |
| Steps | Navigate to `/runs/{runId}/review/H5` |
| Expected Result | Read-only, error, empty evidence, or redirect — **must not** successfully record an H5 Approve/Reject/Request Changes while gate is not H5 |
| Cleanup | — |
| Automation Notes | Attempt decision API via UI; expect disablement or 4xx surfaced |

---

## 9. Phase 5 — Golden paths

### BRW-P5-GOLDEN-01 — All-pass

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Full stack; mock or live LLM; S6 mode documented |
| Test Data | Default golden requirement; reviewer `qa-lead` |
| Steps | New Run → wait H1 → Approve → wait H2 → Approve → wait H3 → Approve → wait execution pass → H4 Approve → H5 Approve → observe S11 / completed |
| Expected Result | Run `completed`; each gate decision recorded; S11 PASS (or mock equivalent); Reports shows S9 for run; Test Cases / Scripts / Executions catalogs reflect the run |
| Cleanup | Note `run_id` |
| Automation Notes | Poll Run Detail / pending gate; confirm dialogs on each Approve |

### BRW-P5-GOLDEN-02 — Execution failure path

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Stack up; force S6 failure (bad base URL, failing target app, or controlled mock failure) |
| Test Data | Requirement that compiles; target that fails assertions |
| Steps | New Run → Approve H1/H2/H3 → observe failed execution → open H4 → confirm S7 classification visible → H4 Approve → H5 review → complete S11 |
| Expected Result | Failure classification visible in UI; H4/H5 still reachable; **S11 reflects actual gate rules** (not a fake all-green if policy fails); catalogs/reports truthful |
| Cleanup | Note `run_id` |
| Automation Notes | Distinguish mock S6 failure vs real Playwright fail |

---

## 10. Phase 5.5 — Live state / polling / multi-tab

### BRW-P55-001 — Running → H1 transition and refresh

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Orchestrator + Gateway |
| Test Data | Golden requirement |
| Steps | Start run; observe Running; refresh while waiting; poll until H1; open review |
| Expected Result | UI recovers after refresh; gate appears without requiring hard reload forever; no stuck blank state |
| Cleanup | Continue or abandon run |
| Automation Notes | Poll interval aligned with UI (~few seconds) |

### BRW-P55-002 — Approve advances without stale UI

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Pending H1 |
| Test Data | Reviewer set |
| Steps | Approve H1; watch Run Detail / workspace |
| Expected Result | UI leaves H1 pending; advances to next running/paused state without showing stale “still H1 pending” after reload |
| Cleanup | — |
| Automation Notes | After confirm, wait for navigation or status change |

### BRW-P55-003 — Second tab reflects decision

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Pending gate |
| Test Data | Same `run_id` in two tabs |
| Steps | Open run/review in tab A and B; Approve in A; refresh or wait in B |
| Expected Result | Tab B shows updated state (no longer pending same decision); cannot double-approve successfully |
| Cleanup | — |
| Automation Notes | Two browser contexts |

---

## 11. Phase 6 — Gate decision variants

### BRW-P6-001 — Approve advances pipeline

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Pending gate Hn |
| Test Data | Reviewer + optional comment |
| Steps | Approve with confirm |
| Expected Result | Pipeline advances toward expected next stage (or next pending gate) |
| Cleanup | — |
| Automation Notes | Per-gate or sample H1+H2 |

### BRW-P6-002 — Request Changes revises and reopens gate

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Pending H1 (or H2/H3); LLM available |
| Test Data | Comment: “Clarify password rules” |
| Steps | Request Changes → confirm → wait |
| Expected Result | Prior review decision `changes_requested`; stage enters `{gate}_revising` then **new pending** at same gate; `artifact_version` bumps; run **stays alive** (not terminal failed) |
| Cleanup | Approve or reject afterward |
| Automation Notes | Matches `request_changes_and_revise`; see orchestrator smoke test |

### BRW-P6-003 — Reject hard-stops

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Pending gate |
| Test Data | Reject comment |
| Steps | Reject → confirm |
| Expected Result | `status=failed`, `current_stage={gate}_rejected`; pipeline does not resume; further Approve of that pending row fails |
| Cleanup | — |
| Automation Notes | Distinct from Request Changes |

### BRW-P6-004 — Duplicate approval rejected

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Pending gate |
| Test Data | — |
| Steps | Approve twice rapidly (two confirms or second tab) |
| Expected Result | Only one gate decision accepted; second attempt errors or no-ops without corrupting state |
| Cleanup | — |
| Automation Notes | Race with two contexts |

### BRW-P6-005 — Approval after terminal / spent pending rejected

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Gate already rejected **or** already changes_requested on that review row |
| Test Data | — |
| Steps | Attempt Approve again on spent gate |
| Expected Result | Rejected / controls disabled; no resume after reject |
| Cleanup | — |
| Automation Notes | After Request Changes, approve the **new** pending row (allowed); approving the old row is not |

### BRW-P6-006 — Refresh mid-review; server authoritative

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Pending gate; typed unsaved comment |
| Test Data | Draft comment text |
| Steps | Type comment; refresh without submitting; separately submit a decision then refresh |
| Expected Result | Unsaved draft may reset; after submit, refresh shows persisted decision/state from server |
| Cleanup | — |
| Automation Notes | localStorage reviewer name may persist (`loadReviewer`) |

### BRW-P6-007 — Approve without reviewer blocked

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Pending gate |
| Test Data | Empty reviewer |
| Steps | Clear Reviewer; click Approve |
| Expected Result | Approve disabled or validation blocks; no API decision |
| Cleanup | — |
| Automation Notes | Buttons disabled when `!reviewer.trim()` |

### BRW-P6-008 — Already-completed gate controls disabled

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Completed run or past gate |
| Test Data | — |
| Steps | Open `/runs/{id}/review/H1` after H1 already approved |
| Expected Result | Decision controls disabled or decisions rejected; evidence may still be readable |
| Cleanup | — |
| Automation Notes | Pair with BRW-P4-006 |

### Planned (not executable today)

| ID | Note |
| --- | --- |
| BRW-P6-PLANNED-001 | Terminal Request Changes (`*_changes_requested` / no resume) — **not current product behavior**; do not automate as pass criteria until backend changes |

---

## 12. Phase 7 — Honesty / integration states

### BRW-P7-001 — No unsupported integration presented as active

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Default local env |
| Test Data | — |
| Steps | Visit Settings, CI/CD, Knowledge, Dashboard CI panel |
| Expected Result | Unsupported integrations not labeled Connected/active falsely |
| Cleanup | — |
| Automation Notes | Cross-check `/integrations/status` |

### BRW-P7-002 — Mock CI visibly identified as mock

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | `CI_GATE_MODE=mock` (typical local) |
| Test Data | — |
| Steps | Dashboard CI section + Settings CI/CD + CI/CD page |
| Expected Result | Mock / not connected called out in plain language |
| Cleanup | — |
| Automation Notes | Copy such as “Production Jenkins is not connected” / `CI_GATE_MODE=mock` |

### BRW-P7-003 — Knowledge Base cannot be edited

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Knowledge page |
| Test Data | — |
| Steps | Open Knowledge Base; search for Add/Edit/Delete |
| Expected Result | Read-only; no write controls that claim to mutate KB |
| Cleanup | — |
| Automation Notes | Settings also states read-only |

### BRW-P7-004 — No MCP claim

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Settings |
| Test Data | — |
| Steps | Read Playwright integration row |
| Expected Result | MCP: no / not claimed as MCP-driven |
| Cleanup | — |
| Automation Notes | `playwright_test · MCP: no` |

### BRW-P7-005 — Reports do not fabricate flaky history

| Field | Value |
| --- | --- |
| Priority | P0 |
| Preconditions | Reports page; preferably a completed run |
| Test Data | Run with S9 |
| Steps | Open Reports; inspect for historical flaky trends |
| Expected Result | Current-run S9 (or empty honest state); **no** invented flaky-history charts/trends |
| Cleanup | — |
| Automation Notes | Settings “Flaky store” honesty |

### BRW-P7-006 — Unknown route placeholder

| Field | Value |
| --- | --- |
| Priority | P2 |
| Preconditions | — |
| Test Data | `/ui/this-route-does-not-exist` |
| Steps | Navigate to unknown path under `/ui/` |
| Expected Result | Not-found placeholder with title/description; shell still usable |
| Cleanup | — |
| Automation Notes | “Not found” placeholder page |

---

## 13. Phase 8 — Responsive / a11y smoke

Still **smoke-level**, not a full WCAG audit.

### BRW-P8-001 — Viewports

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | — |
| Test Data | 1920×1080, 1280×800, 768×1024 |
| Steps | Resize; exercise Dashboard, Run Detail, Review workspace |
| Expected Result | Nav usable; review panel and code viewer usable; no clipped critical CTAs |
| Cleanup | — |
| Automation Notes | Playwright `setViewportSize` |

### BRW-P8-002 — Keyboard and focus

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Pending review |
| Test Data | — |
| Steps | Tab to Approve/Reject; open confirm modal; verify focus; Escape/cancel behavior |
| Expected Result | Controls keyboard-reachable; visible focus; modal focus management adequate for smoke; code viewer scrollable/keyboard usable enough to read |
| Cleanup | — |
| Automation Notes | Focus trap best-effort smoke |

### BRW-P8-003 — Names, headers, color

| Field | Value |
| --- | --- |
| Priority | P1 |
| Preconditions | Pages with tables |
| Test Data | — |
| Steps | Spot-check tables and buttons |
| Expected Result | Tables have headers; buttons have accessible names; critical status not conveyed by color alone (text/pill labels present) |
| Cleanup | — |
| Automation Notes | StatusPill text + tone |

---

## 14. Test-case format

Every case in this plan uses:

```text
ID
Priority          (P0 | P1 | P2)
Preconditions
Test Data
Steps
Expected Result
Cleanup
Automation Notes
```

ID pattern: `BRW-P{phase}-{nnn}` or `BRW-P5-GOLDEN-0x` / `BRW-P55-00x`.

---

## 15. Priority / regression matrix

### P0 — Release blocking

| Area | Cases |
| --- | --- |
| Phase 0 shell | BRW-P0-001…004 |
| New Run happy / empty / double / XSS | BRW-P2-001, 002, 004, 005 |
| Run Detail state | BRW-P3-001, 002 |
| H1–H5 evidence | BRW-P4-001…005 |
| Golden all-pass | BRW-P5-GOLDEN-01 |
| Reject + Request Changes (revise) | BRW-P6-002, 003, 007 |
| Honesty | BRW-P7-001…005 |
| Approve advances | BRW-P6-001 |

### P1 — Important regression

| Area | Cases |
| --- | --- |
| Pending count consistency | BRW-P1-003 |
| New Run errors / slow / gateway | BRW-P2-006…008 |
| Timeline click / share | BRW-P3-003, 004 |
| Wrong-gate URL | BRW-P4-006 |
| Failure golden path | BRW-P5-GOLDEN-02 |
| State sync | BRW-P55-001…003 |
| Duplicate / late decisions | BRW-P6-004…006, 008 |
| Responsive / a11y smoke | BRW-P8-001…003 |
| Optional metadata / catalogs | BRW-P2-003, BRW-P1-001…002 |

### P2 — Extended

| Area | Cases |
| --- | --- |
| Unknown route | BRW-P7-006 |
| Deep nav / large-data UI | Extend later as needed |

### Suggested execution order

1. Phase 0–1 (no LLM)
2. Phase 2–3 (include failure injection where feasible)
3. Phase 4 seeded paused runs + wrong-gate
4. Phase 5.5 then Phase 5 GOLDEN-01 (mock LLM/S6 for CI speed)
5. GOLDEN-02 with forced S6 failure
6. Phase 6–8

---

## 16. Related test plans

| Suite | Document |
| --- | --- |
| Browser E2E (this file) | [`test_plan.md`](test_plan.md) |
| API / Contract | [`docs/api-test-plan.md`](docs/api-test-plan.md) |
| Full pipeline walkthrough | [`docs/end-to-end-flow.md`](docs/end-to-end-flow.md) |
| Resilience | [`docs/resilience-test-plan.md`](docs/resilience-test-plan.md) |
| Domain QA scenarios | [`docs/domain-scenarios.md`](docs/domain-scenarios.md) |
| UI API contract | [`docs/ui-api-contract.md`](docs/ui-api-contract.md) |

Stub documents above hold deferred content; expand them without bloating this browser plan.

---

## Appendix A — Route map

| Path | Page |
| --- | --- |
| `/ui/` | Dashboard |
| `/ui/runs/new` | New Run |
| `/ui/runs` | Runs list |
| `/ui/runs/:runId` | Run Detail |
| `/ui/runs/:runId/review/:gate` | Review workspace (H1–H5) |
| `/ui/reviews` | Reviews |
| `/ui/test-cases` | Test Cases |
| `/ui/scripts` | Scripts |
| `/ui/executions` | Executions |
| `/ui/reports` | Reports |
| `/ui/knowledge` | Knowledge Base |
| `/ui/cicd` | CI/CD |
| `/ui/settings` | Settings |

## Appendix B — Pipeline reference

```text
S1 → S2 → [H1] → S3 → S4 → [H2] → S5 (+ compile) → [H3]
  → S6 → S7 → S8 → S9 → [H4] → S10 → [H5] → S11
```

Human decisions: Approve (resume), Request Changes (revise + reopen), Reject (terminal fail).
