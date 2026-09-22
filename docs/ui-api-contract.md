# QAZen UI — Run State & API Contract (Phase 0)

Canonical contract for the React SPA and Review API read extensions.
All UI pages must use the same mapping; do not re-interpret `status` / `current_stage` ad hoc.

## Pipeline nodes (display order)

| id | label | kind |
|----|-------|------|
| S1 | Normalize | ai |
| S2 | Analyze | ai |
| H1 | Requirement Review | human |
| S3 | Test Cases | ai |
| S4 | Test Data | ai |
| H2 | Test Case Review | human |
| S5 | Automation | ai |
| Compile | Compile | deterministic |
| H3 | Script Review | human |
| S6 | Execute | ai |
| S7 | Analyze | ai |
| S8 | Security | deterministic |
| S9 | Report | deterministic |
| H4 | Execution Review | human |
| S10 | Summary | deterministic |
| H5 | Release Review | human |
| S11 | CI Gate | deterministic |

Product sequence:

`S1 → S2 → H1 → S3 → S4 → H2 → S5 → Compile → H3 → S6 → S7 → S8 → S9 → H4 → S10 → H5 → S11`

## Artifact type → node

| artifact.type | node |
|---------------|------|
| s1_normalized_requirement | S1 |
| s2_ambiguity_analysis | S2 |
| s3_test_cases | S3 |
| s4_test_data | S4 |
| s5_automation_model | S5 |
| s5_compiled_playwright | Compile |
| s6_execution_result | S6 |
| s7_classification | S7 |
| s8_boundary_scan | S8 |
| s9_report | S9 |
| s9_allure_results | S9 (secondary) |
| s10_release_summary | S10 |
| s11_cicd_status | S11 |

Human gates have no skill artifact type; evidence is prior-stage artifacts + `human_reviews` rows.

## DB inputs

From `runs`:

- `status`: `pending` \| `running` \| `paused` \| `completed` \| `failed` \| `cancelled`
- `current_stage`: e.g. `S1`…`S10`, `Compile`, `S11`, `H1_pending`…`H5_pending`, `H1_revising`…`H5_revising`, `H1_rejected`…`H5_rejected`
- `pending_gate`: from latest `human_reviews` where `decision = 'pending'` → `H1`…`H5` \| `null`

Orchestrator writes `status=running` and `current_stage=<node>` at the **start** of each long node (`S1`, `S2`, `S3`, `S4`, `S5`, `Compile`, `S6`, `S7`, `S8`, `S9`, `S10`), before LLM / compiler / Playwright. End-of-node writes remain `H*_pending` + `paused`, or `S11` + `completed`. Request-changes writes `{gate}_revising` until the first revision node starts.

### Runtime → UI contract

Displayed state is derived only from `status`, `current_stage`, `pending_gate`, reviews, and artifacts. The client must not advance the timeline from elapsed time. `uiStatus=revising` only when `current_stage` is `H1_revising`…`H5_revising`.

| Runtime state | `status` | `current_stage` | `pending_gate` | UI (`progressMessage` / action) |
| --- | --- | --- | --- | --- |
| S1 executing | running | S1 | null | Normalizing the requirement… |
| S2 executing | running | S2 | null | Analyzing ambiguities… |
| H1 waiting | paused | H1_pending | H1 | Action Required |
| S3 executing | running | S3 | null | Generating test cases… |
| S4 executing | running | S4 | null | Generating test data… |
| H2 waiting | paused | H2_pending | H2 | Action Required |
| S5 executing | running | S5 | null | Generating automation… |
| Compile | running | Compile | null | Compiling Playwright… |
| H3 waiting | paused | H3_pending | H3 | Action Required |
| S6 executing | running | S6 | null | Running tests… |
| S7 executing | running | S7 | null | Classifying failures… |
| S8 executing | running | S8 | null | Scanning boundaries… |
| S9 executing | running | S9 | null | Building the report… |
| H4 waiting | paused | H4_pending | H4 | Action Required |
| S10 executing | running | S10 | null | Writing the release summary… |
| H5 waiting | paused | H5_pending | H5 | Action Required |
| S11 / done | completed | S11 | null | Completed |
| Request-changes in flight | running | H*_revising | null | Revising the prior phase, then this gate will reopen. |

## Shared UI state: `RunUiState`

Produced by `deriveRunUiState()` in [`web/src/lib/runState.ts`](../web/src/lib/runState.ts).

```ts
uiStatus: "running" | "awaiting_review" | "revising" | "completed" | "failed" | "rejected" | "cancelled"
currentNodeId: PipelineNodeId
actionRequired: boolean
actionGate: "H1" | "H2" | "H3" | "H4" | "H5" | null
currentLabel: string           // e.g. "H3 — Script Review"
runHealth: "on_track" | "blocked" | "failed"
primaryCta: "open_review" | "view_report" | "none"
stopRunAvailable: false        // v1: no Orchestrator cancel API
shareAction: "copy_url"
pipelineNodes: Array<{
  id, label, kind,
  state: "completed" | "current" | "pending" | "failed" | "approved"
}>
listStatusPill: {
  key: "in_progress" | "awaiting_review" | "completed" | "failed" | "rejected" | "cancelled"
  label: string
}
progressMessage: string | null   // running/revising working copy; null when paused/terminal
```

### Mapping rules (summary)

1. If `current_stage` matches `H*_rejected` → `uiStatus=rejected`, that gate `failed`, prior nodes completed.
2. Else if `current_stage` matches `H*_revising` → `uiStatus=revising`, that gate `current`.
3. Else if `pending_gate` or `*_pending` → `uiStatus=awaiting_review`, gate `current` (amber), `primaryCta=open_review`.
4. Else if `status=completed` (typically `current_stage=S11`) → all nodes completed, `primaryCta=view_report`.
5. Else if `status=failed` → `uiStatus=failed`; current node from stage or last artifact.
6. Else if `status=running` with an explicit node stage (`S1`…`S10`, `Compile`) → that node `current` (blue), `progressMessage` from the contract table.
7. Else infer frontier from latest artifacts + reviews (first incomplete node).

**Stop Run:** always `stopRunAvailable=false` in v1. At gates use Open Review → Approve / Request Changes / Reject.

**Request Changes:** iterative revise loop (not a hard stop). Reject is terminal.

## Pass rate (dashboard)

```json
{
  "pass_rate": 0.864,
  "pass_rate_display": "86.4%",
  "pass_rate_basis": "Based on classified executable results",
  "pass_rate_note": "Unclassified failures are excluded from the denominator (S9 rules)."
}
```

## Decision semantics (mutations — existing)

| Action | Endpoint | Effect |
|--------|----------|--------|
| Approve | `POST /runs/{id}/approve` | Resume graph |
| Request Changes | `POST /runs/{id}/request-changes` | Re-run prior phase; same gate reopens; artifact version bumps |
| Reject | `POST /runs/{id}/reject` | `status=failed`, `{gate}_rejected` |

Body: `{ "reviewer": string, "comment"?: string }`

## Planned Review API endpoints (Phase 2)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/runs` | filters: status, stage, limit, offset; include requirement summary |
| GET | `/runs/{run_id}` | detail + optional embedded `ui_state` |
| GET | `/runs/{run_id}/artifacts` | list |
| GET | `/runs/{run_id}/artifacts/{artifact_id}` | content |
| GET | `/runs/{run_id}/timeline` | audit events for AuditTimeline |
| GET | `/runs/{run_id}/lineage` | ordered versions for ArtifactLineage |
| GET | `/runs/{run_id}/test-cases` | |
| GET | `/runs/{run_id}/scripts` | compiled Playwright |
| GET | `/runs/{run_id}/executions` | |
| GET | `/runs/{run_id}/review` | existing |
| GET | `/runs/{run_id}/history` | existing |
| GET | `/dashboard/summary` | includes pass_rate_basis |
| GET | `/reviews/pending` | |
| GET | `/knowledge` | read-only |
| GET | `/integrations/status` | Mock / Not Configured / Connected |
| POST | `/runs` | `input.raw` required; metadata passthrough optional |

See TypeScript shapes in [`web/src/api/types.ts`](../web/src/api/types.ts).

## New Run input contract

**Supported**

- `input.raw` (requirement text) — required
- `requirement_id` — optional

**Passthrough metadata** (stored in `input`, displayed if present; not integrated systems)

- `requirement_type`, `environment`, `base_url`, `branch`, `labels`

**Do not present as integrated**

- Jira sync, application version control, release ID orchestration

## Honest integration labels

| Area | Allowed labels |
|------|----------------|
| CI/CD | Mock, Configured, Connected, Not Configured |
| Knowledge Base | Read-only; writes Not wired |
| Flaky history | No historical flaky-test data loaded |
| Playwright | Playwright Test runner (not MCP) |
| Stop Run | Cancellation not available yet |

## Phase 0 verification

- [x] Document written
- [x] `deriveRunUiState` + ≥8 fixture tests (`npm test` in `web/` — 14 passed)
- [x] API TypeScript types for Phase 2
- [ ] Human confirmation before Phase 1
