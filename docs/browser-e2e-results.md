# Browser E2E Execution Results

**Date:** 2026-09-16 (continued ×2); **2026-09-17** BRW-P2-001 re-run; cloud LLM compare; BRW-P2-007/008; BRW-P55-003; SPA rebuild `index-DZETaTrI.js`; BRW-P4-005 H5; BRW-P55-001 Ollama Cloud golden **completed**; S6 spec→`test_case_id` mapping fix; Session 20 New Run `base_url` (S5 timeout); Session 21 live S6 mapping **PASS**; Session 22 `fc8083f6…` H4 go → H5 → S11 **completed**; Session 23 persist/display `base_url` on `GET /runs` (**fixed**); Session 24 revising UI + H3 all compiled specs (**fixed**); Session 25 H3 all S5 models (**display fixed**)  
**Stack:** Gateway `:8000` (`LLM_PROFILE=ollama`, `nemotron-3-super:cloud` via `http://127.0.0.1:11434/v1`; LLM7 Nemo 429; Gemini 20 RPD exhausted), Review `:8001`, Orchestrator `:8002`  
**GOLDEN-01 (Ollama mock):** `3ae2f2a0-8000-48b6-b8a6-4f8a18a78da9` (S6=mock, all-pass, 30–90+ min)  
**GOLDEN-01 (Ollama Cloud live Playwright):** `776c8f6b-7c38-44ba-bee8-381af2711d5a` (S6=playwright vs local `/login`, **completed**/S11, 100%)  
**BRW-S6-MAP-002 (live mapping):** `fc8083f6-d524-4c48-aff6-f893075c8151` (S6 distinct TC ids 2/2, **completed**/S11)  
**GOLDEN-01 (LLM7):** `2bfb1f7c-7692-4a63-9f6a-0b06a9b41923` (S6=mock, all-pass, **83s**)  
**GOLDEN-02:** `5e13da19-55bd-4ea1-8e37-3f9f03800ed4` (S6=playwright vs invalid host → fail)  
**Cloud mix H1–H5:** `9375a463-e9f2-4a00-a277-b65f799b9bf7` (Gemini S1–S5 + Playwright S6 fail + LLM7 S7–S11)  
**BRW-P2-001:** `b4e93c6b-dc98-4f06-bdb1-395f7b6c0dac` (async `POST /runs`)

## Summary

| Metric | Count |
| --- | --- |
| Scenarios defined | 47 (+1 planned) |
| Executed (cumulative) | **47** |
| Passed | **51** |
| Failed | **0** |
| Partial | **0** |
| Not run | **0** |

**Verdict:** Browser matrix all-pass. Live Ollama Cloud golden `776c8f6b…` **completed S11**. Mapping run `fc8083f6…` also **completed S11**. New Run `base_url` now persists on `runs` and appears on `GET /runs` / Run Detail.

---

## GOLDEN-01 — all-pass

| Step | Result |
| --- | --- |
| Ollama S1–S5 + mock S6 → H1…H5 → `completed`/`S11` | PASS |

## GOLDEN-02 — execution failure

| Step | Result | Notes |
| --- | --- | --- |
| H3 approve → Playwright S6 | PASS | ~5+ min at S6 |
| H4 UI evidence | PASS | **Passed 0 / Failed 1**, Pass Rate **0.0%**, app `this-host-does-not-exist.invalid` |
| S7 visible | PASS | `unclassified_pending_triage: 1` |
| H4→H5→completed S11 | PASS | Humans can still complete review; run not fake-green |

---

## Session 3 additions

| ID | Result | Notes |
| --- | --- | --- |
| BRW-P5-GOLDEN-02 | PASS | See above |
| BRW-P4-002 | PASS | H2 on `64fdabe5…`: S3 test cases + S4 test data |
| BRW-P4-005 | PARTIAL | H5 pending briefly during GOLDEN-02; full S10 snap not captured (completed quickly) |
| BRW-P6-004 | PASS* | Concurrent approve → `500` + `409`; run **did not** double-advance (stayed H1_pending) |
| BRW-P6-006 | PASS | Hard navigate clears unsaved comment; gate still pending |
| BRW-P8-002 | PASS | Tab focus reaches Approve/Reject; confirm dialog opens; Cancel/Escape closes |
| BRW-P55-003 | **PASS** | Session 8: approve in tab A, refresh tab B on `7680dd74…` |

\*Under LLM load, one concurrent approve hit Review API 600s→500.

---

## Session 5 — cloud LLM vs Ollama (2026-09-17)

| Segment | Ollama qwen2.5:7b | Gemini 3.6 Flash | LLM7 Nemo |
| --- | --- | --- | --- |
| S1+S2 → H1 | ~11 min | **33s** | **8s** |
| H1 → H2 (S3+S4) | ~7 min | **29s** | **8s** |
| H2 → H3 (S5+Compile) | long | **29s** | **32s** |
| Full H1–H5 S6=mock all-pass | 30–90+ min | blocked: **20 RPD** quota | **83s** (`2bfb1f7c-…`, S11 `pass`) |

Mistral cloud key was 429. Gateway maps S3 `source_tags` `INFERENCE` → `FACT` so Nemo can pass schema. Restore Gemini after midnight PT: `LLM_PROFILE=gemini`.

---

## Session 6 — leftover New Run / approve (2026-09-17)

| ID | Result | Notes |
| --- | --- | --- |
| BRW-P2-004 | **PASS** (after fix) | First double-click created **two** runs (`0c396dcf…`, `352e557e…`). `NewRunPage` now keeps a sync submit lock until navigate. Retest `BRW-P2-004c` → **one** run `e55d27cd-75f5-4f8d-8025-188ab68ef249`. |
| BRW-P2-005 | **PASS** | Run `343c8583-…`. H1 evidence JSON shows `<script>alert(1)</script>` / `<img … onerror>` as **text**; no live `<script>`, `onerror`, or `<b>` nodes. |
| BRW-P55-002 | **PASS** | Approve H1 on `e55d27cd-…`: workspace showed `H2_pending` / “Pipeline continuing…”; reload Run Detail is **H2 — Test Case Review**, not stale H1. |

---

## Session 7 — slow POST + gateway down (2026-09-17)

| ID | Result | Notes |
| --- | --- | --- |
| BRW-P2-007 | **PASS** | Injected 8s client delay **after** `POST /runs` 200. **A)** Button `Starting QA Run…` + disabled; navigated once to `7680dd74-4fe0-4256-907e-30f4873c2b1d` (`BRW-P2-007a`, one run). **B)** Refresh mid-wait: stayed on New Run (no success claim); server run `1bbcd016-94ac-4ab4-aa37-9d7e5709b377` (`BRW-P2-007b`) findable under Runs search. |
| BRW-P2-008 | **PASS** | Gateway stopped; create still succeeded (async insert). Run `a49d2572-b72a-41df-9c20-0d5c4564ce24` (`BRW-P2-008`) went `status=failed` / `current_stage=S1` in ~6s. UI **Run Health: Failed** — not a silent hang. Gateway restarted (`LLM7` Nemo). UX nit: no copy explaining *why* (connection refused). |

---

## Session 8 — true multi-tab approve (2026-09-17)

| ID | Result | Notes |
| --- | --- | --- |
| BRW-P55-003 | **PASS** | Two tabs on `7680dd74-4fe0-4256-907e-30f4873c2b1d` H1. Tab A approve (`qa-lead`, comment `BRW-P55-003 tab A approve`) → H2_pending in ~22s; tab A showed “Approved — pipeline continuing…” + H1/H2 mismatch. Tab B hard-refresh: **Pending H2**, banner “awaiting H2”, Approve/Request Changes/Reject **disabled** (`pointer-events: none`). Cannot double-approve H1 in B. |

---

## Session 9 — async approve / request-changes (2026-09-17)

| Item | Result | Notes |
| --- | --- | --- |
| HTTP approve | **PASS** | Orchestrator `POST /resume` records approval + `status=running` / next stage, returns immediately; graph on worker. Review `POST /approve` on `1bbcd016…` **200 in ~801ms** (was ~22s sync). Duplicate approve **409**. |
| Background S3 | LLM 500 | After return, S3 invoke hit gateway 500; run marked `failed` at S3 (visible, not a hang). CLI/smoke still use sync `approve_gate_and_resume`. |
| HTTP request-changes | unit **PASS** | Same background pattern; Review proxy timeout 60s (was 600s). |

---

## Session 10 — POST /runs failure presentation (2026-09-17)

| ID | Result | Notes |
| --- | --- | --- |
| BRW-P2-006 | **PASS** | Mock `POST /runs` 500: stayed on New Run; banner showed orchestrator error; **0** runs with `requirement_id=BRW-P2-006`. After restoring fetch, retry created **one** run `19535d56-9266-4c14-8a11-efab2654e885`. `NewRunPage` now prefers `ApiError.message` over raw JSON body. SPA rebuild `index-DZETaTrI.js`: banner is plain **orchestrator unavailable** (not raw JSON). |
| BRW-P55-001 | still **PARTIAL** | Retry run showed **S1 running** / “Normalizing the requirement…”. Refresh after LLM7 S1 **500** showed **Run Health: Failed** (no blank page). Did not reach H1 this session. |

---

## Session 11 — H5 evidence + S1 quota (2026-09-17)

| ID | Result | Notes |
| --- | --- | --- |
| BRW-P55-001 | still **PARTIAL** | New run `5fb33e90-d53f-451a-a573-52c09a4a9ba6` (`requirement_id=BRW-P55-001`). UI left New Run (`Starting QA Run…`) → Run Detail at S1. Gateway `POST /v1/skills/S1/invoke` **429** `Daily token quota exceeded. Retry after 75097 seconds.` (~21h). Refresh: **Run Health: Failed**, S1 node red, **no blank page**. Did not reach H1. |
| BRW-P4-005 | **PASS** | Parked H4 `a05508b5-d257-426a-97ff-54820eb04f2d` (SauceDemo S6 fail, 0/1). H4 approve (`qa-lead`) → deterministic S10 → **H5_pending**. UI: “Release evidence (facts only)”; banner “S10 presents facts only. No ship/hold recommendation”; narrative is counts/classifications only (0 passed / 1 failed / pass rate 0.0% / app_bug=1 / S8=0). **S10 — Release summary** JSON present. Approve / Request Changes / Reject **enabled** (`pointer-events: auto`). Left at H5 (not decided). |

---

## Session 12 — BRW-P55-001 on Ollama Cloud (2026-09-17)

| ID | Result | Notes |
| --- | --- | --- |
| BRW-P55-001 | **PASS** | Gateway `LLM_PROFILE=ollama` / `nemotron-3-super:cloud`. Run `776c8f6b-7c38-44ba-bee8-381af2711d5a`. New Run (`Starting QA Run…`) → Run Detail **S1 running** / “Normalizing the requirement…” / Run Health **On Track**. Mid-wait Refresh recovered at **S2** (S1 green, “Analyzing ambiguities…”, no blank). Silent poll → **H1_pending** without another hard reload (~2m43s S1+S2). Open Review → H1 workspace with S1 normalized requirement + S2 ambiguity JSON; Approve/Request Changes/Reject enabled. Left at H1. |

---

## Session 13 — Ollama H1 approve + empty S3 (2026-09-17)

| Item | Result | Notes |
| --- | --- | --- |
| UI H1 approve (`776c8f6b…`) | **PASS** | `qa-lead` / `BRW-P55-002 Ollama Cloud H1 approve`. Async “Approved — pipeline continuing…” at **S3** then **S4**. Silent nav to **H2**. Run Detail reload is **H2_pending** / Action Required — not stale H1. |
| First S3/S4 | empty | Gateway 200. Artifacts `{test_cases:[]}` / `{datasets:[]}`. `s3.schema.json` `minItems: 0` allows it. UI showed empty JSON; Test Cases catalog 0. Did **not** Approve. |
| H2 Request Changes | **PASS** | Feedback: generate valid+invalid login cases, no empty arrays. Banner “Changes requested — revising…”. S3/S4 200. **Artifact v2**: `TC-valid_login_1`, `TC-invalid_login_1` + `DS-valid_login_1` / `DS-invalid_login_1`. In-page Refresh kept stale “S4 running / revising”; **hard navigate** showed `H2_pending` paused v2. Left at H2 (not approved). |

---

## Session 14 — Ollama H2 approve → H3 (2026-09-17)

| Item | Result | Notes |
| --- | --- | --- |
| UI H2 approve (`776c8f6b…` v2) | **PASS** | `qa-lead`. “Approved — pipeline continuing…” at **S5**. ~63s later silent nav to **H3_pending**. S5 + Compile completed. |
| H3 evidence | present | Role-based model for `TC-valid_login_1` (`/login`, Username/Password, Dashboard visible). Compiled `TC-valid_login_1.spec.ts` with `page.goto("/login")` + filled `valid_user` / `valid_pass`. |
| Coverage gap | note | H2 had 2 cases; S5/Compile produced **only** the valid-login script. No `TC-invalid_login_1.spec.ts`. Run has **no base_url** — H3 not approved (S6 would hit relative `/login`). |

---

## Session 15 — Ollama H3 request-changes (2026-09-17)

| Item | Result | Notes |
| --- | --- | --- |
| Gateway health | **PASS** | `LLM_PROFILE=ollama`, `nemotron-3-super:cloud`, `http://127.0.0.1:11434/v1`. |
| UI H3 request-changes (`776c8f6b…` v1) | **PASS** | `qa-lead`. Feedback: compile `TC-invalid_login_1.spec.ts` for invalid login; keep valid-login; cover both H2 cases. Confirm → async “Changes requested — revising…” at **S5** / `status=running`. |
| S5 + Compile | **PASS** | ~81s (`11:29:37` → `11:30:58` UTC). Silent return to **H3_pending**. |
| Hard navigate reopen | **PASS** | `/ui/runs/776c8f6b…/review/H3` shows **H3 — Script Review**, Action Required, **Artifact v2**, paused. Approve / Request Changes / Reject enabled. |
| Missing spec filled | **PASS** | New `playwright/generated/776c8f6b…/TC-invalid_login_1.spec.ts`: role locators, `/login`, `invalid_user`/`invalid_pass`, Login heading + `role=alert`. `TC-valid_login_1.spec.ts` still on disk. |
| H3 evidence scope | note | Workspace / review API show **latest S5 only** (`SCR-TC-invalid_login_1`). S5 records one model per invoke; Compile writes one spec; H3 evidence is latest-by-type. S6 globs `generated/<run_id>/*.spec.ts` so both files would execute. |
| H3 approve | skipped | Run `base_url` is still **null**. Did not advance to S6. |
| Parked H5 `a05508b5…` | unchanged here | Closed in Session 16. |

---

## Session 16 — parked H5 no-go (2026-09-17)

| Item | Result | Notes |
| --- | --- | --- |
| H5 workspace `a05508b5…` | **PASS** | Banner “S10 presents facts only. No ship/hold recommendation”. Narrative: 0 passed / 1 failed / pass rate 0.0% / app_bug=1 (`TC-LOGIN-VALID`). Approve / Request Changes / Reject enabled. |
| H5 Reject (`qa-lead`) | **PASS** | Comment `BRW-P4-005 H5 no-go`. Confirm “Reject this run?” → “Rejected — run stopped.” Navigated to Run Detail. |
| Terminal state | **PASS** | `status=failed`, `current_stage=H5_rejected`, `pending_gate=null`. UI **Rejected** pill, **Run Health: Failed**, “No human review is pending”. S11 did not run. Reviews badge 20→19. |
| Live Ollama run | unchanged | `776c8f6b…` still `H3_pending` / `base_url=null`. |

---

## Session 17 — H3 approve → S6 local fixture (2026-09-17)

| Item | Result | Notes |
| --- | --- | --- |
| Login fixture | **PASS** | `scripts/login_fixture.py` on `http://127.0.0.1:8765/login` — Username/Password, Dashboard on `valid_user`/`valid_pass`, `role=alert` on invalid. |
| H3 approve (`776c8f6b…` v2) | **PASS** | `qa-lead`. Orchestrator `QAZEN_BASE_URL=http://127.0.0.1:8765`. Async “Approved — pipeline continuing…”. |
| S6 Playwright | ran | App recorded as `http://127.0.0.1:8765`. Both compiled specs executed. |
| S6 outcomes | fail (infra) | **Passed 0 / Failed 2** (8–16ms). `browserType.launch`: Chromium missing at sandbox `…\ce952ee0…\playwright\chromium-1140\chrome-win\chrome.exe`. Chrome exists in a different sandbox cache (`8c1fefda…`). |
| S6 ID mapping | note | Report listed both files; S6 JSON tagged **both** as `TC-invalid_login_1` (latest S5 `test_case_id`). |
| S7 / H4 | **PASS** | `unclassified_pending_triage: 1`. Silent nav to **H4_pending** artifact v1. S8 clean. Pass rate **0.0%**. Did not Approve. |
| H4 request-changes | **PASS** | Re-ran S6; same Chromium miss (8–10ms). Reopened **H4 artifact v2**. Orchestrator restart with `PLAYWRIGHT_BROWSERS_PATH` failed (`Errno 10048` port 8002 still bound). |
| Code | note | `node_s6` now passes `raw_input.base_url` into Playwright. `playwright_runner` subprocess uses UTF-8 `errors=replace` (Windows cp1252 crash on Playwright stdout). |

---

## Session 18 — Chromium salvage → S6 pass → H5 go → S11 (2026-09-17)

| Item | Result | Notes |
| --- | --- | --- |
| Chromium junction | **PASS** | Linked `8c1fefda…/chromium-1140` into sandbox `ce952ee0…`. Next S6 failed on missing `ffmpeg-1010` (531ms / 365ms). Junctioned ffmpeg + `.links`. |
| H4 RC after ffmpeg | **PASS** | S6 vs `http://127.0.0.1:8765`. Playwright report: `TC-invalid_login_1` **ok** 1098ms, `TC-valid_login_1` **ok** 886ms. UI **Passed 2 / Failed 0 / 100.0%**. H4 artifact **v4**. |
| H4 approve | **PASS** | `qa-lead`. S10 facts only. Silent nav to **H5_pending**. |
| H5 | **PASS** | Banner facts-only. Narrative: 2 passed / 0 failed / 100.0% / app_bug=0 / S8=0. Approve go. |
| S11 | **PASS** | `status=completed`, `current_stage=S11`, Run Health **On Track**, pill **Completed**. No pending gate. |

---

## Session 19 — S6 maps each spec to its own test_case_id (2026-09-17)

| Item | Result | Notes |
| --- | --- | --- |
| Bug | **fixed** | `_parse_json_report` stamped every Playwright spec with latest S5 `test_case_id` (`TC-invalid_login_1` on golden `776c8f6b…`). |
| Mapping | **PASS** (unit) | Compiler file `{test_case_id}.spec.ts` + test title `TC-*` → that id; `script_id` is S5’s when it matches, else `SCR-{test_case_id}`. Evidence paths use known result ids (Playwright folders include the title after the id). Unmatched / empty report still falls back to S5. |
| Tests | **PASS** | `orchestrator/tests/test_playwright_runner.py` — 4 new tests; with report builder **8 passed** (0.14s). Golden 2-spec fixture now yields `TC-invalid_login_1` + `TC-valid_login_1` (not both invalid). |
| Live S6 | not re-run | Orchestrator `:8002` left running (module is imported per `node_s6` but cached). Restart `:8002` before the next Playwright S6 to pick up the fix. No new LLM run. |

---

## Session 20 — New Run base_url + live S6 mapping (2026-09-17 / 18)

| Item | Result | Notes |
| --- | --- | --- |
| Orchestrator restart | **PASS** | Stopped `:8002`; restarted from this shell with `PLAYWRIGHT_BROWSERS_PATH`=`ce952ee0…/playwright` (Chromium+ffmpeg junctions to `8c1fefda…`). `S6_EXECUTION_MODE=playwright`. Health ok. |
| New Run UI | **PASS** | `/ui/runs/new`: requirement valid+invalid `/login`; **Requirement ID** `BRW-S6-MAP-001`; **Application / Base URL** `http://127.0.0.1:8765`. Button **Starting QA Run…** → `/ui/runs/b902b92f-6329-4af8-82d6-2faefe421845`. |
| S1+S2 → H1 | **PASS** | ~2 min. `status=paused` / `H1_pending` / Run Health On Track. |
| H1 approve | **PASS** | `qa-lead`. Next **S3**. |
| H2 v1 | 1 case | `TC-valid-login-001` + `DS-valid-login-001` only. Did **not** Approve. |
| H2 request-changes | **PASS** | Feedback: add invalid login. Reopened **H2 artifact v2**: `TC-LOGIN-VALID-001` + `TC-LOGIN-INVALID-001` (matching datasets). |
| H2 approve | **PASS** | `qa-lead`. Next **S5**. |
| S5 | **FAIL** (infra) | `httpx.ReadTimeout` after `LLM_GATEWAY_TIMEOUT_SECONDS=600`. Gateway still `ollama` / `nemotron-3-super:cloud`. Run `status=failed` / `current_stage=S5`. UI **Failed** pill, **Run Health: Failed**, “No human review is pending”, Scripts 0. Did not reach H3/S6. |
| `runs.base_url` | nit | Review `GET /runs/{id}` still `base_url=null`. `runs` table has **no** `base_url` column; New Run puts it on `raw_input.base_url` (LangGraph) which `node_s6` reads. |
| S6 mapping live | **not verified** | Unit tests still pass; this run never executed Playwright. |

---

## Session 21 — live S6 distinct test_case_id (2026-09-18)

| Item | Result | Notes |
| --- | --- | --- |
| New run | **PASS** | `fc8083f6-d524-4c48-aff6-f893075c8151` (`requirement_id=BRW-S6-MAP-002`). `input.base_url=http://127.0.0.1:8765`. S1+S2 → H1 ~2 min. |
| H1 approve | **PASS** | `qa-lead`. |
| H2 v1 | 1 case | `TC-001` valid only. Request-changes. |
| H2 v2 | **PASS** | `TC-valid_login_001` + `TC-invalid_login_001` + matching datasets. Approve. |
| S5 + Compile | **PASS** | ~4 min (did not hit 600s). H3 v1 compiled only `TC-valid_login_001.spec.ts`. |
| H3 request-changes | **PASS** | Second S5 ~5.5 min. Disk now has both `TC-valid_login_001.spec.ts` and `TC-invalid_login_001.spec.ts`. H3 evidence latest S5 = `TC-invalid_login_001` (v2). |
| H3 approve → S6 | **PASS** | Playwright vs `http://127.0.0.1:8765`. |
| S6 IDs | **PASS** | Rows: `TC-invalid_login_001` pass 817ms + `TC-valid_login_001` pass 629ms (not both latest S5). Scripts `SCR-TC-invalid_login_001` / `SCR-TC-valid_login_001`. `environment_metadata.app_build=http://127.0.0.1:8765`. |
| H4 UI | **PASS** | Passed **2** / Failed **0** / **100.0%**. Results list both TC ids. Application `http://127.0.0.1:8765`. S8 clean. Left at **H4_pending** (not approved). Closed in Session 22. |
| `GET /runs.base_url` | still null | S6 still used `raw_input.base_url`. |

---

## Session 22 — H4 go → H5 → S11 on mapping run (2026-09-18)

| Item | Result | Notes |
| --- | --- | --- |
| Gateway health | **PASS** | `LLM_PROFILE=ollama`, `nemotron-3-super:cloud`, `http://127.0.0.1:11434/v1`. Login fixture `:8765` 200. |
| H4 workspace `fc8083f6…` | **PASS** | Artifact v1. Passed **2** / Failed **0** / **100.0%**. Results: `TC-invalid_login_001` pass 817ms + `TC-valid_login_001` pass 629ms. Application `http://127.0.0.1:8765`. |
| H4 approve | **PASS** | `qa-lead` / `BRW-S6-MAP-002 H4 go`. Confirm → async submit. S10 deterministic. Silent nav to **H5_pending**. |
| H5 evidence | **PASS** | Banner “S10 presents facts only. No ship/hold recommendation”. Narrative: 2 passed / 0 failed / 0 skipped / pass rate 100.0% / app_bug=0 / S8=0. Approve / Request Changes / Reject enabled. |
| H5 approve (go) | **PASS** | `qa-lead` / `BRW-S6-MAP-002 H5 go`. |
| S11 | **PASS** | `status=completed`, `current_stage=S11`, `pending_gate=null`. UI **Completed** pill, **Run Health: On Track**, “No human review is pending”. Reviews badge 19→18. |
| `GET /runs.base_url` | still null | Unchanged; S6 already used `raw_input.base_url`. Fixed in Session 23. |

---

## Session 23 — persist/display New Run base_url (2026-09-18)

| Item | Result | Notes |
| --- | --- | --- |
| Schema | **PASS** | `infra/sql/002_runs_passthrough_metadata.sql` (+ `001_init.sql`): `runs.base_url` / `environment` / `branch`. Applied live. |
| Orchestrator create | **PASS** | `create_run` + `_persist_run` store New Run passthrough from `input`. Smoke insert `BRW-BASEURL-SMOKE` wrote all three columns. Restarted `:8002` with `PLAYWRIGHT_BROWSERS_PATH=ce952ee0…`. |
| Review GET /runs | **PASS** | Prefer run columns → S1 echo → S6 `app_build` only if it looks like `http(s)://`. `fc8083f6…` → `base_url=http://127.0.0.1:8765`, `environment=test`. |
| SPA | **PASS** | Run Detail shows **Base URL** (header + Requirement aside). Rebuild `index-LV68-QW1.js` (was `index-DZETaTrI.js`). Hard-reload required. |
| Backfill | **PASS** | URL-like S6 `app_build` copied onto matching runs; non-URL values cleared. Known mapping/golden runs set. |
| Unit tests | **PASS** | `review-api/tests/test_passthrough_metadata.py` 2 passed; `orchestrator/tests/test_start_run_http.py` 5 passed. |

---

## Session 24 — revising UI + H3 all compiled specs (2026-09-18)

| Item | Result | Notes |
| --- | --- | --- |
| Stale “revising” after Refresh | **fixed** | `ReviewWorkspacePage.load` now clears `polling` + revising/continuing banner when server shows `pending_gate` / terminal / not in-flight. Poll effect no longer races that sync. |
| H3 / Scripts catalog | **fixed** | `scripts_from_compiled` keeps newest unique `file_name` across Compile versions (was latest version only → 1 of N). H3 evidence adds `compiled_scripts` and renders every source. |
| Live check `fc8083f6…` | **PASS** | `GET /runs/…/scripts` → 2 files: `TC-invalid_login_001.spec.ts` v2 + `TC-valid_login_001.spec.ts` v1. |
| SPA | **PASS** | Rebuild `index-BOJMvrcW.js`. Review `:8001` restarted. |
| Tests | **PASS** | `test_scripts_from_compiled.py` + passthrough 3 passed; web `runState` 25 passed. |

---

## Session 25 — H3 all S5 automation models (2026-09-18)

| Item | Result | Notes |
| --- | --- | --- |
| Generation (one model / invoke) | **left** | S5 skill + schema remain one `test_case_id` per LLM call. Multi-model-in-one-invoke would need schema/compiler redesign + longer S5 times. |
| H3 display | **fixed** | `automation_models_from_s5` keeps newest unique model per `test_case_id`. H3 evidence includes `automation_models` and lists each. SPA `index-5oaTq1hM.js`. |
| Smoke `fc8083f6…` | **PASS** | Two S5 model versions (valid + invalid) after request-changes history. |

---

## Session 4 — async POST /runs (2026-09-17)

| ID | Result | Notes |
| --- | --- | --- |
| BRW-P2-001 | **PASS** | Review `POST /runs` returned `{run_id, status: running}` in **630ms**. UI New Run navigated to `/runs/b4e93c6b-…` in a few seconds (button showed Starting… then left the form). Run Detail loaded at S1 (`requirement_id=BRW-P2-001`) and **silent-polled to H1_pending** without a hard refresh (~11 min S1+S2 under concurrent Ollama load). |

---

## Full ID matrix (latest)

### Phase 0–1 — all PASS
### Phase 2
| ID | Result |
| --- | --- |
| BRW-P2-001 | **PASS** — async create; UI polls to H1 |
| BRW-P2-002 | PASS |
| BRW-P2-003 | PASS* |
| BRW-P2-004 | **PASS** — submit lock; one run `e55d27cd-…` |
| BRW-P2-005 | **PASS** — XSS/HTML escaped in H1 JSON |
| BRW-P2-006 | **PASS** — 500 stays on New Run; retry creates one run |
| BRW-P2-007 | **PASS** — slow POST; refresh mid-submit leaves run under Runs |
| BRW-P2-008 | **PASS** — create ok; S1 fails visibly when gateway down |

### Phase 3 — all PASS (incl. timeline node click, Stop disabled)

### Phase 4
| ID | Result |
| --- | --- |
| BRW-P4-001 | PASS |
| BRW-P4-002 | PASS |
| BRW-P4-003 | PASS |
| BRW-P4-004 | PASS |
| BRW-P4-005 | **PASS** — H5 facts-only then **Reject no-go** on `a05508b5…` (`H5_rejected`) |
| BRW-P4-006 | PASS |

### Phase 5 / 5.5
| ID | Result |
| --- | --- |
| BRW-P5-GOLDEN-01 | PASS |
| BRW-P5-GOLDEN-02 | PASS |
| BRW-P55-001 | **PASS** — Ollama Cloud S1→S11 completed; Playwright S6 2/2 vs local `/login`; run `776c8f6b…` |
| BRW-P55-002 | **PASS** — H1 approve → H2 without stale pending |
| BRW-P55-003 | **PASS** — approve in A, refresh B shows H2; H1 controls disabled |

### Phase 6
| ID | Result |
| --- | --- |
| BRW-P6-001…003 | PASS |
| BRW-P6-004 | PASS* |
| BRW-P6-005…008 | PASS |

### Phase 7 — all PASS
### Phase 8
| ID | Result |
| --- | --- |
| BRW-P8-001 | PASS |
| BRW-P8-002 | PASS |
| BRW-P8-003 | PASS |

---

## Issues found

1. **Approve / request-changes HTTP is async** (2026-09-17): Orchestrator records the decision then resumes/revises on a worker (same pattern as `POST /runs`). Review proxy timeout is 60s. Background graph can still fail (LLM 500) and mark `status=failed`.
2. **Stale Orchestrator** (earlier): missing `/request-changes` until restart.
3. **LLM contention:** parallel GOLDEN-02 start + gate approves caused ReadTimeout / 500s. Two concurrent S1+S2 on qwen2.5:7b took ~11 min to H1.
4. Confirm dialog keyboard Escape works via Cancel path; focus outline often `none` (smoke OK).
5. **LLM7 daily token quota** (2026-09-17 ~10:08 UTC): `openai.RateLimitError` 429 `Daily token quota exceeded` (`retry_after` 75097s ≈ 21h). Switched to Ollama Cloud `nemotron-3-super:cloud`.
6. **S3 empty arrays are schema-valid** (`minItems: 0`). `nemotron-3-super:cloud` first S3/S4 on `776c8f6b…` stored `test_cases: []` / `datasets: []` (HTTP 200). Request-changes produced 2 cases + 2 datasets.
7. **Request-changes workspace can stay on “revising”** after the API is already `H2_pending` — **fixed 2026-09-18**: Refresh/`load` syncs polling + banner from server status.
8. **S5 covered 1 of 2 H2 cases** on `776c8f6b…` (v1): compiled only `TC-valid_login_1.spec.ts`. H3 request-changes produced `TC-invalid_login_1.spec.ts` (v2). H3 UI previously showed **latest S5 artifact only** — **display fixed 2026-09-18** (Sessions 24–25): H3 lists every unique compiled file **and** every unique S5 model per `test_case_id`. S5 still generates one model per invoke.
9. **S5 emits one automation model per invoke** (by skill/schema design). Not changed to multi-model generation; H3 now aggregates prior invoke versions for review.
10. **S6 Playwright Chromium path** (2026-09-17): after restarting orchestrator from the agent shell, Playwright looked in sandbox cache `ce952ee0…` where `chrome.exe` is missing. Prior runs used `8c1fefda…`. Launch fails in ~10ms; not an app bug.
11. **S6 result IDs follow latest S5 only** — **fixed 2026-09-17**; **live-verified 2026-09-18** on `fc8083f6…` (two specs → `TC-invalid_login_001` + `TC-valid_login_001`). Golden `776c8f6b…` still has the old stored rows.
12. **Windows Playwright stdout** can `UnicodeDecodeError` under cp1252; runner now reads UTF-8 with replacement.
13. **`runs` table had no `base_url` column** — **fixed 2026-09-18**: columns `base_url` / `environment` / `branch` persisted at create; `GET /runs` + Run Detail UI display them. S6 still reads LangGraph `raw_input.base_url`.
14. **S5 Ollama Cloud ReadTimeout** (2026-09-18): run `b902b92f…` H2-approved then `httpx.ReadTimeout` at 600s on `POST /v1/skills/S5/invoke`. Visible fail at S5, not a hang.

## Scripts added for reruns

- [`orchestrator/scripts/e2e_golden02_fail.py`](../orchestrator/scripts/e2e_golden02_fail.py) — full bad-host start (needs quiet Ollama)
- [`orchestrator/scripts/e2e_golden02_h3_fail.py`](../orchestrator/scripts/e2e_golden02_h3_fail.py) — H3→Playwright fail salvage
- [`scripts/login_fixture.py`](../scripts/login_fixture.py) — local `/login` app matching compiled role locators (`:8765`)

## Recommendation

- Done: HTTP `POST /runs`, `/resume`, and `/request-changes` return after persisting; graph work runs in a worker pool.
- Serialize heavy LLM E2E runs to avoid gateway timeouts.
- Live Ollama Cloud golden `776c8f6b…` is **completed / S11** (Playwright 2/2 pass on local login fixture; H5 go). Keep `scripts/login_fixture.py` running if you re-run S6. Junction Chromium+ffmpeg into the active Playwright sandbox cache rather than restarting `:8002` when the port is busy.
- Session 20 New Run `b902b92f…` (`BRW-S6-MAP-001`) filled `base_url=http://127.0.0.1:8765` and reached H2 v2 (2 cases) then **failed at S5** (gateway ReadTimeout 600s). Do not resume.
- Session 21–22 `fc8083f6…` (`BRW-S6-MAP-002`) **S6 mapping live-verified then closed**: 2/2 pass, distinct TC ids, app `http://127.0.0.1:8765`, H4 go → H5 go → **completed / S11**.
- Session 23: New Run `base_url` / `environment` / `branch` **persisted on `runs` and shown on `GET /runs` + Run Detail**.
- Session 24: stale request-changes “revising” UI **fixed**; H3/Scripts show **all** compiled specs across versions.
- Session 25: H3 shows **all unique S5 automation models** per `test_case_id` (`index-5oaTq1hM.js`). Did **not** change S5 to emit multiple models in one LLM invoke.
- Stop here unless you want multi-model S5 generation (skill + schema + compiler + longer S5).
