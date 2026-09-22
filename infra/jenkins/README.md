# Jenkins + QAZen CI gate

This folder holds a **stub** Jenkins pipeline for the pilot. Full AWS ECS/EKS hosting is still deferred.

## How S11 pushes status

| Mode | Env | Behavior |
|---|---|---|
| `mock` (default) | `CI_GATE_MODE=mock` | Records pass/fail/blocked in the `s11_cicd_status` artifact only |
| `http` | `CI_GATE_MODE=http` + `CI_GATE_ENDPOINT` (or `cicd_endpoint` in `ci_gate_config.json`) | POSTs JSON to the endpoint after H5 |

Optional: `CI_GATE_TOKEN` → `Authorization: Bearer …` on the HTTP push.

Payload shape (abbreviated):

```json
{
  "run_id": "...",
  "status": "pass|fail|blocked",
  "threshold_applied": { "min_pass_rate": 0.95 },
  "fail_reasons": [],
  "linked_summary": { "run_id": "...", "artifact_type": "s10_release_summary" },
  "push_timestamp": "2026-09-15T00:00:00Z",
  "factual_excerpt": "..."
}
```

## Using the Jenkinsfile

1. Create a Pipeline job pointing at [`Jenkinsfile`](Jenkinsfile).
2. Set `QAZEN_ORCHESTRATOR_URL` / `QAZEN_REVIEW_URL` to reachable hosts.
3. Run the job to start a QAZen run (or pass `RUN_ID`).
4. Complete H1–H5 in the Review UI, then continue the Jenkins `input` step.

Do not store API keys or webhook secrets in this repo.
