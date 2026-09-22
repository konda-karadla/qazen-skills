# Agentic AI QA testing framework — architecture overview

**Purpose of this document:** a single read for anyone joining this project to understand what we're building, how it's structured, and where things stand. Not a spec — see `AGENT_INSTRUCTIONS.md` for the binding rules, and each `skill.md` file for how an individual stage actually works.

---

## 1. What this is

An AI-assisted QA framework that takes a requirement (a BRD, a Jira ticket, a user story) and carries it all the way through to an executed, reported, release-gated test suite — with a human checkpoint at every stage where judgment actually matters. It is **not** a fully autonomous testing agent. Nothing in this framework approves its own output; every meaningful decision — is this requirement clear, are these test cases right, does this script assert the right thing, is this release safe to ship — is made by a person, using facts and evidence the framework prepares for them.

**Scope for v1:** UI and API layers only. Database validation is a deliberate, documented future extension — not built now.

---

## 2. The core design decision: skills, not agents

Early drafts of this framework were agent-based — separate autonomous AI agents each owning a piece of the pipeline. We moved away from that. The current design has:

- **11 stateless `skill.md` files** — each one is a prompt template, not a running service. It has no memory of any other call. The LLM Gateway reads it fresh, assembles it with the shared rulebook and the relevant input, and makes one completion call.
- **One deterministic Orchestrator** — plain code, not an LLM. It sequences the skills, tracks run state, and owns every pause/resume decision at the human checkpoints. It never generates content itself.
- **One shared rulebook, `AGENT_INSTRUCTIONS.md`** — the non-negotiable rules every skill call inherits: never approve your own output, never modify a test to force a pass, never silently assume an undefined business rule, always escalate ambiguity instead of guessing.

Why this matters for anyone building on this: a skill.md file is something you *edit like a prompt*, not something you deploy or version like a microservice. If you're used to thinking in agents, recalibrate — there isn't one here.

---

## 3. The pipeline — 11 skills, 5 human gates

Requirement goes in one end, a release decision comes out the other. Every skill-phase is followed by a human gate before the next phase can start:

| Stage | Skill(s) | What happens |
|---|---|---|
| Normalize & analyze | S1, S2 | Structure the raw input; tag every claim FACT / ASSUMPTION / INFERENCE / DECISION; flag ambiguity |
| **H1 — Requirement sign-off** | — | Human confirms the requirement is unambiguous enough to build test cases from |
| Design | S3, S4 | Generate test case specs (BVA/EP); generate or mask test data |
| **H2 — Test case review** | — | Human confirms the generated test cases are correct and complete |
| Automate | S5 | Generate Playwright scripts (UI actions + API calls) from approved test cases |
| **H3 — Script/code review** | — | Human confirms the automation asserts the *right thing*, not just something that passes |
| Execute & assess | S6, S7, S8 | Run the suite; classify every failure (app bug / flaky / environment / automation error); scan every action against security boundaries |
| **H4 — Execution & stability review** | — | Human reviews failure classifications and stability trends |
| Report & release | S9, S10, S11 | Aggregate results and trends; produce a factual (never a recommendation-phrased) release summary; push pass/fail status to CI/CD |
| **H5 — Release sign-off** | — | Human-only go/no-go decision. Nothing upstream is allowed to phrase itself as a recommendation. |

**Why H3 specifically matters:** it's the gate that stops automation from confidently asserting the wrong thing while still technically passing — a failure mode that's easy to miss without a dedicated review step.

---

## 4. Where it runs

Everything is **containerized and centrally hosted — not something each person clones and runs locally.** A few reasons that matters:

- Environment pinning (browser version, OS, runtime, app build) has to be exact for evidence to be trustworthy. A container guarantees that; a laptop drifts.
- The Domain Knowledge Store and Evidence Store have to be shared across the team, not fragmented per clone — otherwise confirmed business rules and audit trails scatter.
- CI builds the container image from `main` on every merge, so everyone is provably running the same version of the rules, not whatever they last pulled.

Local execution still has a place — headed-mode debugging while writing a script — but any run whose results count toward a metric or a gate comes from the shared, pinned container.

---

## 5. System components

```
Trigger (prompt, Jira, webhook, requirement change)
        │
        ▼
┌───────────────────────────────────────┐
│   Hosted — Docker container on AWS    │
│                                        │
│   Orchestration                       │
│   (LangGraph + AGENT_INSTRUCTIONS.md) │
│              │                        │
│   LLM gateway (stateless, one call    │
│   per skill invocation)               │
│              │                        │
│   Playwright MCP                      │
│   (script generation + execution)     │
└───────────────────────────────────────┘
        │              │             │            │
  Human review   Knowledge store  Evidence +   Git → Jenkins
  (H1–H5)        (Postgres)       reports      (CI/CD)
                                   (MinIO +
                                   Allure)
```

**Open-source pieces and why:**
- **LangGraph** — the Orchestrator's engine. Built-in durable execution (checkpoints per step, resumes after a crash) and a native pause/resume mechanism that maps directly onto H1–H5.
- **microsoft/playwright-mcp** — the tool layer. Drives both UI actions and raw API/HTTP calls, so one connector covers both layers in scope.
- **MinIO** — self-hosted, S3-compatible object storage for screenshots, videos, traces, HAR files.
- **Allure Report** (or ReportPortal for heavier ML-based failure triage) — turns raw results into human-readable reports.
- **Postgres** — backs the Domain Knowledge Store and doubles as LangGraph's checkpoint store, so run state and confirmed business rules live in the same durable place.

**What's custom, with no open-source substitute:** the actual governance logic — S2's ambiguity tagging, S4's masking rules, S7's failure classification, S8's security scan, S10's release summary, S11's threshold logic. That logic is what makes this framework ours; the rest is plumbing.

---

## 6. How a requirement change gets handled (Agile)

There's no separate "update" mechanism. A changed requirement is just a new trigger — it re-enters at S1/S2 like any other input, gets re-tagged, and only the parts of the Domain Knowledge Store or test suite it actually affects get regenerated and pushed back through H2/H3. Superseded rules are marked superseded, not deleted, so the history stays traceable.

---

## 7. Current status

- `AGENT_INSTRUCTIONS.md` — v2.0, rewritten for the skill-based architecture, DB removed from scope, 5 gates. Locked as the binding rulebook.
- `S3_test_case_generation.md` — drafted, first of the 11 skills.
- **Build order for the remaining Phase 1 slice** (no gates yet, proving the pipeline mechanically): S1, S5, S6, S9.
- **Not yet started:** S2, S4, S7, S8, S10, S11 (Phases 2–4), the Orchestrator code itself, and the container/hosting setup.

---

## 8. Open decisions the team should weigh in on

- **Trigger mechanism** — manual (CLI/UI) to start, or wired to Jira/webhooks from day one?
- **Human review interface** — a dedicated web UI, or something lighter (Slack, Jira comments) for v1?
- **LLM model for the Gateway** — not yet chosen.
- **Deployment target** — AWS-native (ECS/EKS, matching existing Bedrock infrastructure) vs. a simpler single-host Docker Compose setup for the pilot.

*End of overview.*
