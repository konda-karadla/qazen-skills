# QAZen — Progress / Handoff

**Last updated:** 2026-09-16  
**Phase complete:** Production UI Phases 0–8 (`web/` SPA at `/ui/`) — **confirmed**  
**Next:** Choose backlog item (see §6). Sprint 7 Impact is a separate Java `test-platform` repo — do not mix into this chat unless asked.

Use this file as the single entry point when continuing in a new chat. Also read:
- [requirement.md](requirement.md), [review.md](review.md), [README.md](README.md)
- Jenkins stub: [infra/jenkins/README.md](infra/jenkins/README.md)

---

## 1. What this project is

AI-assisted, skill-based QA framework (not autonomous agents): 11 skills, deterministic Orchestrator (H1–H5), LLM Gateway, human gates only. **v1:** UI + API (Playwright). DB validation deferred.

---

## 2. Locked decisions

| Decision | Choice |
|---|---|
| Gates / slice | H1–H5; full S1…S11 path |
| S8 / S11 | Deterministic policy engines |
| S9 / S10 | Deterministic builders; Allure on S9 |
| LLM (live) | **`LLM_PROFILE=ollama`** (qwen2.5:7b). Switch later: `LLM_PROFILE=openai` + key |
| LLM (tests) | `LLM_PROVIDER=mock` in process env |
| CI push | `CI_GATE_MODE=mock` (tests) or `http` (webhook) |
| Infra pilot | Docker Compose; AWS later |
| Review | API + Web UI `/ui/` with recent-runs queue |

---

## 3. Built

| Area | Status |
|---|---|
| S1–S11 + schemas + H1–H5 | Done |
| `LLM_PROFILE` ollama/openai/mock | Done — [`llm-gateway/app/config.py`](llm-gateway/app/config.py) |
| Allure / S11 HTTP / Jenkins stub / Review UI | Done |
| Local helper | [`scripts/start-local-ollama.ps1`](scripts/start-local-ollama.ps1) |

### Deferred

- [ ] AWS ECS/EKS hosting
- [ ] Production Jenkins credentials / shared lib
- [ ] Allure CLI baked into CI image

---

## 4. Local LLM vs OpenAI switch

**Now (default in `.env`):**

```
LLM_PROFILE=ollama
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=qwen2.5:7b
```

**Later (cloud):** set `LLM_PROFILE=openai`, set `OPENAI_API_KEY`, use `https://api.openai.com/v1`, restart gateway only. Do not commit keys.

Check: `GET http://localhost:8000/health` → `llm_profile`, `openai_base_url`, `openai_model` (no key).

E2e one-shot: `.\scripts\run-local-e2e.ps1` (or `-SmokeOnly` for quick S1).

**2026-09-16:** `run-local-e2e.ps1 -SmokeOnly` → **RUN_LOCAL_SMOKE_OK** (Ollama S1, attempts=2).
**2026-09-15:** `e2e_ollama.py` completed **OLLAMA_E2E_OK** through H5.

---

## 5. Resume

```powershell
cd infra; docker compose up -d
.\scripts\start-local-ollama.ps1
# Gateway :8000 (LLM_PROFILE=ollama), Review :8001 (/ui/), Orchestrator :8002
```

---

## 6. Next backlog

1. AWS ECS/EKS + production Jenkins wiring
2. Allure CLI in container image

---

## 7. Next-chat prompt

```
Continue QAZen from PROGRESS.md (repo: C:\Users\KondaBabuKaradla\Documents\QAZEN_SKILLS).

Local pilot done. Live LLM default: LLM_PROFILE=ollama. Tests: LLM_PROVIDER=mock.
Do not commit .env or print secrets.

Next: AWS ECS/EKS and/or Allure CLI in CI image.
```

---

*End of progress handoff.*
