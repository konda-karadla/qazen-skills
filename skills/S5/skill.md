# S5 — Test Script Generation

**Skill type:** Stateless — read fresh by the LLM Gateway on every invocation
**Invoked between:** H2 (Test Case Review) and H3 (Script/Code Review)
**Inherits:** All binding sections of AGENT_INSTRUCTIONS.md, especially Section 13.1 (UI Automation Standard) and Section 13.2 (API Automation Standard) — this skill's job is to make those standards actually happen, not just exist in a separate document.

---

## 1. What this skill does

Converts **one** H2-approved test case into an **automation model** — a structured, declarative description of the UI actions and/or raw HTTP/API requests needed to exercise that case, per the layer(s) tagged on it, using S4's test data. The Orchestrator invokes this skill **once per H2 test case** (input `s3_output.test_cases` has a single element and `focus_test_case_id` matches it) so H3 receives a compiled spec for every case. This skill does **not** write Playwright code. It decides *what* the automation must do and assert; a separate, deterministic Automation Model Compiler (Orchestrator tooling, not an LLM call) turns that model into the actual `.spec.ts` file presented at H3.

This split exists on purpose: an LLM writing free-form code can silently weaken an assertion or paper over a missing locator in ways that are hard to spot in review. A structured model is easy to validate against a JSON schema, easy to diff at H3 without reading code, and impossible to compile into something that skips a required assertion — the compiler either has the assertion in the model or it doesn't emit one.

---

## 2. Required inputs

- H2-approved test case specifications from S3 (expected results, layer tagging, traceability ID). When the orchestrator batches, this is exactly one case whose `test_case_id` equals `focus_test_case_id`.
- S4's test data, mapped to that test case
- Target environment scope (least-privilege credentials only, per Section 9)

---

## 3. Required process

**Step 1 — For UI test cases, choose locators in the required order:** role/label/text-based semantic locators first, `data-test-id` attributes next, CSS selectors after that. XPath only as a last resort, and only with a documented reason recorded on the model. Never locate by dynamically generated IDs or framework-specific class names.

**Step 1a — Use exact accessible names; never paraphrase.** Role `name=` values, labels, and heading/button text must match a **confirmed** source character-for-character (requirement text, S3 `input_values` / obligation / expected result, domain knowledge, or an explicit human DECISION). Do **not** invent synonyms or “natural” alternatives (`Login` ≠ `Log in` ≠ `Sign in`; `Username` ≠ `User name`). Prefer the same names already used in this skill’s worked example when the case is the same `/login` Username / Password / Login / Dashboard pattern. If the exact accessible name is unknown, escalate — do not guess. When a name contains spaces or commas, quote it in the locator string (e.g. `role=button[name="Save draft"]`).

**Step 2 — For UI test cases, model waits explicitly, don't leave them implicit.** Default action steps in the model rely on the compiler's built-in auto-wait; add a `wait` step only for network-idle or a specific, justified application-state condition, with the justification recorded on that step. A hard-coded sleep/delay step is never a valid step type — if a test seems to need one, that's a potential application timing bug to escalate, not a step to add.

**Step 3 — For API test cases, model the required assertions as discrete, typed assertion entries:** exact status code (not a status-code family), full response schema validation against the confirmed contract, response time against the configured SLA, and any headers the requirement specifies. Model token acquisition/refresh as its own setup step, isolated from the test's assertions, so an expired token is never misreported as an application failure.

**Step 4 — Model the assertion to match the expected result exactly as S3 stated it** — not a looser version that's easier to get passing. If the exact assertion can't be represented given the current application state, that's a signal to escalate, not to soften. Every assertion step must carry the `test_case_id` field it proves. For “must remain / must not appear / must not open X” outcomes, use assertion type `visible` with `expected_value: false` (or an equivalent negative assertion the schema allows) — never assert that a forbidden element is visible.

**Step 5 — Tag the model with full traceability**: which `test_case_id` it implements, which layer(s) it covers, and which Section 13 standard each locator/wait/assertion choice follows.

---

## 4. Output format

- `script_id`
- `test_case_id` — the S3 output this model implements
- `layer` — UI, API, or both
- `automation_model` — the structured, declarative model (not code):
  - `setup` — preconditions/auth/navigation steps, in order
  - `actions[]` — each with `type` (e.g. `navigate`, `fill`, `click`, `select`, `request`), `locator` or `endpoint`, `value`/`payload` where applicable
  - `assertions[]` — each with `type` (e.g. `visible`, `status_code`, `schema_match`, `response_time`, `header_match`), `target`, `expected_value`, and the `test_case_id`/expected-result line it proves
- `locator_strategy_notes` — if UI: which strategy was used per action, and why, especially if XPath was needed
- `wait_strategy_notes` — if UI: any explicit `wait` steps and their justification
- `assertions_plain` — every assertion restated in plain language, so an H3 reviewer can check the model against the S3 expected result without reading the model's raw structure

### Worked example

```json
{
  "script_id": "SCR-TC-001",
  "test_case_id": "TC-001",
  "layer": "UI",
  "automation_model": {
    "setup": [{ "type": "navigate", "target": "/login" }],
    "actions": [
      { "type": "fill", "locator": "role=textbox[name=Username]", "value": "{{username}}" },
      { "type": "fill", "locator": "role=textbox[name=Password]", "value": "{{password}}" },
      { "type": "click", "locator": "role=button[name=Login]" }
    ],
    "assertions": [
      { "type": "visible", "target": "role=heading[name=Dashboard]", "expected_value": true, "test_case_id": "TC-001" }
    ]
  },
  "locator_strategy_notes": "All locators role-based per Section 13.1; no fallback needed",
  "wait_strategy_notes": "None required; auto-wait sufficient",
  "assertions_plain": ["After valid login, the Dashboard heading must be visible (proves TC-001)."]
}
```

The Automation Model Compiler (deterministic, not this skill) turns this into `tests/login/TC-001.spec.ts`. If the compiler cannot represent a modeled step or assertion in Playwright, that is a compiler defect to fix or a model escalation — never a reason for this skill to fall back to emitting raw code.

---

## 5. NOT permitted to

- Emit raw Playwright/TypeScript code, or any executable script, as this skill's output. The output is always the structured automation model; code generation happens downstream, deterministically.
- Alter a test's assertions or expected outcomes to make it pass. This is the single rule H3 exists to check — do not make H3's job harder by needing to catch this.
- Hardcode a value that masks a real data-dependency the test is supposed to exercise.
- Use a locator strategy or wait strategy that deviates from Section 13.1 without documenting why and flagging it for H3's attention.
- Invent, paraphrase, or “normalize” accessible names (role `name=`, labels, button/heading text) that are not confirmed in the inputs — including near-synonyms of the worked example.
- Assert that a forbidden element is visible when S3 says it must not appear (use `expected_value: false` for `visible` instead).
- Weaken an API assertion (e.g., checking "2xx" instead of the exact required status code) to avoid a failure.
- Model a step or assertion that has no traceable `test_case_id`.
- Generate a model for a test case that hasn't passed H2.

---

## 6. Escalation triggers

- A test case specification is technically infeasible to automate as written (e.g., it requires interacting with an element that has no stable locator of any kind).
- The exact accessible name (button/label/heading) needed for a role locator is not present in the requirement, S3 case, domain knowledge, or other confirmed input — guessing a synonym is not allowed.
- Modeling the assertion exactly as specified would require weakening it to get the test to pass in the current environment.
- A Section 13 standard genuinely cannot be met given the test case as specified (e.g., no SLA is configured for an endpoint the test needs to check response time against).
- A required action or assertion type has no representable step type in the automation model schema (i.e., the model itself needs a new step type before this test case can be modeled at all).

---

*End of S5 skill.md*
