# QAZen API / Contract Test Plan

**Status:** Stub — content deferred.

This document will hold API and contract tests for Review API (`:8001`), Orchestrator (`:8002`), and LLM Gateway (`:8000`).

Browser E2E coverage lives in [`../test_plan.md`](../test_plan.md).  
Pipeline behavior reference: [`end-to-end-flow.md`](end-to-end-flow.md).  
UI shapes: [`ui-api-contract.md`](ui-api-contract.md).

## Intended scope (to expand)

- `POST /runs`, approve / reject / request-changes
- Dashboard, reviews, artifacts, catalogs
- Schema validation and error codes
- Idempotency and duplicate decision handling

Do not duplicate browser journey cases here.
