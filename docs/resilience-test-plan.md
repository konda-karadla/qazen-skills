# QAZen Resilience Test Plan

**Status:** Stub — content deferred.

This document will hold failure-injection and recovery tests (Gateway down, Postgres restart, Orchestrator restart, MinIO upload failure, LLM malformed JSON, timeouts).

Browser E2E master plan: [`../test_plan.md`](../test_plan.md).  
Implemented pipeline behavior: [`end-to-end-flow.md`](end-to-end-flow.md).

## Intended scope (to expand)

- Service unavailability and restart recovery via LangGraph checkpoints
- Partial evidence / MinIO best-effort failure
- LLM retry / invalid JSON paths

Keep chaos catalogs out of the browser E2E document.
