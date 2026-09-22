/**
 * Mirrors schemas/s5.schema.json. Kept intentionally in sync by hand for
 * Phase 0 -- if this drifts from the schema, schema validation in the LLM
 * Gateway is the source of truth, not this file.
 */

export type StepType = "navigate" | "fill" | "click" | "select" | "check" | "wait" | "request";

export interface Step {
  type: StepType;
  locator?: string;
  endpoint?: string;
  value?: unknown;
  payload?: unknown;
  target?: string;
  justification?: string;
}

export type AssertionType =
  | "visible"
  | "status_code"
  | "schema_match"
  | "response_time"
  | "header_match"
  | "text_match";

export interface Assertion {
  type: AssertionType;
  target: string;
  expected_value: unknown;
  test_case_id: string;
}

export interface AutomationModel {
  setup: Step[];
  actions: Step[];
  assertions: Assertion[];
}

export interface S5Output {
  script_id: string;
  test_case_id: string;
  layer: "UI" | "API" | "both";
  automation_model: AutomationModel;
  locator_strategy_notes?: string;
  wait_strategy_notes?: string;
  assertions_plain: string[];
}
