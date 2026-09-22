# QAZen Agentic QA Automation Framework

Skill-based, human-gated QA automation pipeline. See [requirement.md](requirement.md) for the
full architecture rationale, [review.md](review.md) for the implementation review that shaped
the build order, [docs/end-to-end-flow.md](docs/end-to-end-flow.md) for a step-by-step walkthrough
of one run, and the plan file for the phased roadmap.

**Continuing in a new chat?** Start with [PROGRESS.md](PROGRESS.md) — current phase status,
resume commands, and a copy-paste prompt for the next session.

**Phase 0–2 + S10/S11/H5 + Allure + Review UI status: done.** Pipeline:

`S1 -> S2 -> [H1] -> S3 -> S4 -> [H2] -> S5 -> [H3] -> S6 -> S7 -> S8 -> S9 -> [H4] -> S10 -> [H5] -> S11`

S9/S10 are **deterministic** builders (facts only at S10 — never go/no-go phrasing). S8/S11
are deterministic policy engines. S9 also writes **Allure 2** results under
`reports/allure-results/<run_id>/` (set `ALLURE_ENABLED=false` to skip). S11 pushes with `CI_GATE_MODE=mock` (default) or `http` (webhook to `CI_GATE_ENDPOINT`).
Jenkins stub: `infra/jenkins/`. Review Web UI: `http://localhost:8001/ui/` (Start a run + recent-runs queue; Request changes revises the prior stage).


## Repository layout

```
AGENT_INSTRUCTIONS.md   binding rulebook every skill inherits
skills/S1..S11/skill.md  the 11 stateless skill prompt templates
schemas/                 JSON Schemas for skill outputs (s1..s11)
llm-gateway/              stateless completion service (prompt builder + provider + schema validation/retry)
orchestrator/             LangGraph Orchestrator: sequencing, Postgres checkpointing, gate pause/resume
automation-compiler/      deterministic S5 automation_model JSON -> Playwright .spec.ts compiler
review-api/               human-review HTTP API + React SPA at /ui/ (gates H1-H5)
web/                      React + Vite + Tailwind source for the Review SPA (see web/README.md)
infra/                    docker-compose.yml (Postgres + MinIO) + Postgres DDL
playwright/generated/     compiler output lands here (gitignored)
reports/allure-results/   Allure 2 results per run (gitignored)
```

## Running it locally

### 1. Start infra (Postgres + MinIO)

```powershell
cd infra
docker compose up -d
```

### 2. Create a venv and install the Python services

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r llm-gateway\requirements.txt -r orchestrator\requirements.txt -r review-api\requirements.txt
```

### 3. Start the three services (separate terminals)

**Live LLM (default):** repo-root `.env` has `LLM_PROFILE=ollama` talking to `http://127.0.0.1:11434/v1`.
Current model is `nemotron-3-super:cloud` (Ollama Cloud; still has Ollama usage caps). Local fallback:
`OPENAI_MODEL=qwen2.5:7b`. Gateway `/health` reports `llm_profile` + `openai_base_url` (never the API key).

**Gemini:** set `LLM_PROFILE=gemini` and `GEMINI_API_KEY` / `OPENAI_API_KEY` from https://aistudio.google.com/apikey,
comment the Ollama `OPENAI_*` lines, restart gateway.

**Ollama helper:** `.\scripts\start-local-ollama.ps1`. Claude Code is separate and does not serve QAZen:
`ollama launch claude --model nemotron-3-super:cloud`.

**One-shot (recommended):** start Docker + all 3 services + e2e:

```powershell
cd C:\Users\KondaBabuKaradla\Documents\QAZEN_SKILLS
.\scripts\run-local-e2e.ps1 -SmokeOnly   # quick S1 check
.\scripts\run-local-e2e.ps1              # full H1-H5 e2e
.\scripts\run-local-e2e.ps1 -SkipE2e     # services only
.\scripts\run-local-e2e.ps1 -Stop        # stop services started by the script
```

**Paid OpenAI:** `LLM_PROFILE=openai`, set `OPENAI_API_KEY`, restart gateway only.
**Mistral backup:** keep `MISTRAL_API_KEY` in `.env`; set `LLM_PROFILE=mistral` and restart the gateway to fail over.
**Groq (optional):** `LLM_PROFILE=groq` + Groq key — free TPM is tight for QAZen prompts.

```powershell
# LLM Gateway (port 8000) — live: leave LLM_PROVIDER unset or openai (loads .env LLM_PROFILE=ollama)
# Tests/CI only: $env:LLM_PROVIDER = "mock"
cd llm-gateway; ..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000

# Orchestrator (port 8002)
$env:DATABASE_URL = "postgresql://qazen:qazen_local_dev@localhost:5432/qazen"
$env:LLM_GATEWAY_URL = "http://localhost:8000"
cd orchestrator; ..\.venv\Scripts\python.exe -m uvicorn app.api:app --port 8002

# Review API (port 8001)
$env:DATABASE_URL = "postgresql://qazen:qazen_local_dev@localhost:5432/qazen"
$env:ORCHESTRATOR_URL = "http://localhost:8002"
cd review-api; ..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001
```

### 4. Drive a run

**Preferred:** open the Review UI and use **New Run** (paste the requirement — no manual API):

`http://localhost:8001/ui/`

SPA source lives in [`web/`](web/) — see [`web/README.md`](web/README.md) for `npm run dev` / `npm run build` (build output → `review-api/static`).

Then Approve / Request changes / Reject each gate in the browser. **Request changes** re-runs the prior stage and opens the same gate again with new evidence. **Reject** stops the run.

**API alternative:**

```powershell
# Start a run (Orchestrator or Review API proxy)
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/runs -ContentType "application/json" `
  -Body '{"input": {"raw": "Users must log in with valid credentials and reach the dashboard."}}'

# See what's pending
Invoke-RestMethod -Uri http://127.0.0.1:8001/runs/<run_id>/review

# Approve / reject / request changes
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/runs/<run_id>/approve -ContentType "application/json" `
  -Body '{"reviewer": "qa-lead", "comment": "looks good"}'
```

Repeat approve for **H1, H2, H3, H4, and H5** in order — or stay in the Review UI with `?run_id=<run_id>`.

After H3 the suite runs (S6→S7→S8→S9 + Allure results); H4 presents the S9 report; H4 approve
runs S10; H5 presents the factual release summary; H5 approve runs S11 (mock CI push) and
completes the run.

### 5. Compile an approved automation model into Playwright

```powershell
cd automation-compiler
npm install
npx tsx src/cli.ts <path-to-s5-output.json> [path-to-flat-test-data.json]
# writes playwright/generated/<test_case_id>.spec.ts
```

## Tests

```powershell
$env:LLM_PROVIDER = "mock"; $env:PYTHONPATH = "llm-gateway"
.venv\Scripts\python.exe -m pytest llm-gateway\tests -q

$env:DATABASE_URL = "postgresql://qazen:qazen_local_dev@localhost:5432/qazen"
$env:LLM_GATEWAY_URL = "http://localhost:8000"; $env:PYTHONPATH = "orchestrator"
$env:S6_EXECUTION_MODE = "mock"; $env:CI_GATE_MODE = "mock"
.venv\Scripts\python.exe -m pytest orchestrator\tests -q   # requires the gateway running

cd automation-compiler; npx tsx --test tests\compile.test.ts
```

## What's next

See [PROGRESS.md](PROGRESS.md): AWS ECS/EKS, Allure CLI in CI image.

CI gate HTTP mode (after H5):

```powershell
$env:CI_GATE_MODE = "http"
$env:CI_GATE_ENDPOINT = "https://your-jenkins-or-webhook/…"
# optional: $env:CI_GATE_TOKEN = "…"
```

See [infra/jenkins/README.md](infra/jenkins/README.md).

For offline orchestrator tests keep `S6_EXECUTION_MODE=mock` and `CI_GATE_MODE=mock`. For real
browser runs: `$env:S6_EXECUTION_MODE = "playwright"` (default), install Playwright browsers
under `playwright/` (`npm install` then `npm run install-browsers`), and ensure MinIO is up.

To watch S6 clicks in a real Chromium window (local HITL), restart the orchestrator with:

```powershell
$env:S6_HEADED = "true"
$env:S6_SLOW_MO_MS = "250"   # optional; slows each Playwright action
```

Headless remains the default. Trace Viewer / video artifacts are still produced after the run when enabled.

Allure results land in `reports/allure-results/<run_id>/`. To build HTML (optional):
install the [Allure CLI](https://allurereport.org/docs/install/), then
`allure generate reports/allure-results/<run_id> -o reports/allure-report/<run_id> --clean`
(or leave `ALLURE_GENERATE_HTML=true` so the orchestrator tries automatically when the CLI is present).

Review UI smoke:

```powershell
$env:PYTHONPATH = "review-api"
.venv\Scripts\python.exe -m pytest review-api\tests -q
```
