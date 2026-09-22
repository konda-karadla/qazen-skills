# Demo BRD — Sauce Demo UI + ReqRes API

Public demo targets used by QAZen Phase 1 vertical-slice runs. No real PII.

## Files

| File | Purpose |
|------|---------|
| [brd.md](brd.md) | Sample business requirements (UI + API) |

## Feed into a run

With Orchestrator on port 8002:

```powershell
$brd = Get-Content -Raw examples\demo-brd\brd.md
$body = @{ input = @{ raw = $brd } } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8002/runs -ContentType "application/json" -Body $body
```

Or pass a shorter excerpt for S1-only gateway smoke:

```powershell
# See llm-gateway/scripts/smoke_s1_openai.py
```

## Targets

- **UI:** https://www.saucedemo.com — standard demo users (`standard_user` / `secret_sauce`)
- **API:** https://reqres.in — public fake REST API
