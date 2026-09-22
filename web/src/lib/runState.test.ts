import { describe, expect, it } from "vitest";
import { deriveRunUiState, pollFreshness, resolveCurrentNodeId } from "./runState";

describe("resolveCurrentNodeId", () => {
  it("maps H3_pending to H3", () => {
    expect(
      resolveCurrentNodeId({
        status: "paused",
        current_stage: "H3_pending",
        pending_gate: "H3",
      }),
    ).toBe("H3");
  });

  it("maps running S5-equivalent via H3_revising to H3", () => {
    expect(
      resolveCurrentNodeId({
        status: "running",
        current_stage: "H3_revising",
      }),
    ).toBe("H3");
  });

  it("maps S6 running to S6", () => {
    expect(
      resolveCurrentNodeId({
        status: "running",
        current_stage: "S6",
      }),
    ).toBe("S6");
  });

  it("maps running S2 to S2", () => {
    expect(
      resolveCurrentNodeId({
        status: "running",
        current_stage: "S2",
      }),
    ).toBe("S2");
  });

  it("maps running S4 to S4", () => {
    expect(
      resolveCurrentNodeId({
        status: "running",
        current_stage: "S4",
      }),
    ).toBe("S4");
  });

  it("maps running S5 to S5", () => {
    expect(
      resolveCurrentNodeId({
        status: "running",
        current_stage: "S5",
      }),
    ).toBe("S5");
  });

  it("maps running Compile to Compile", () => {
    expect(
      resolveCurrentNodeId({
        status: "running",
        current_stage: "Compile",
      }),
    ).toBe("Compile");
  });

  it("maps completed S11 to S11", () => {
    expect(
      resolveCurrentNodeId({
        status: "completed",
        current_stage: "S11",
      }),
    ).toBe("S11");
  });
});

describe("deriveRunUiState — fixture matrix", () => {
  it("1. running + S5 inferred path: H3_revising → revising at H3", () => {
    const ui = deriveRunUiState({
      status: "running",
      current_stage: "H3_revising",
      artifacts: [
        { type: "s1_normalized_requirement" },
        { type: "s2_ambiguity_analysis" },
        { type: "s3_test_cases" },
        { type: "s4_test_data" },
      ],
    });
    expect(ui.uiStatus).toBe("revising");
    expect(ui.currentNodeId).toBe("H3");
    expect(ui.actionRequired).toBe(false);
    expect(ui.stopRunAvailable).toBe(false);
    expect(ui.pipelineNodes.find((n) => n.id === "H3")?.state).toBe("current");
    expect(ui.listStatusPill.key).toBe("in_progress");
  });

  it("2. paused + pending_gate=H3 → awaiting review, amber current, open_review CTA", () => {
    const ui = deriveRunUiState({
      status: "paused",
      current_stage: "H3_pending",
      pending_gate: "H3",
      artifacts: [
        { type: "s5_automation_model" },
        { type: "s5_compiled_playwright" },
      ],
      reviews: [
        { gate: "H1", decision: "approved" },
        { gate: "H2", decision: "approved" },
        { gate: "H3", decision: "pending" },
      ],
    });
    expect(ui.uiStatus).toBe("awaiting_review");
    expect(ui.currentNodeId).toBe("H3");
    expect(ui.currentLabel).toBe("H3 — Script Review");
    expect(ui.actionRequired).toBe(true);
    expect(ui.actionGate).toBe("H3");
    expect(ui.primaryCta).toBe("open_review");
    expect(ui.runHealth).toBe("blocked");
    expect(ui.pipelineNodes.find((n) => n.id === "Compile")?.state).toBe("completed");
    expect(ui.pipelineNodes.find((n) => n.id === "H3")?.state).toBe("current");
    expect(ui.pipelineNodes.find((n) => n.id === "S6")?.state).toBe("pending");
    expect(ui.pipelineNodes.find((n) => n.id === "H1")?.state).toBe("approved");
    expect(ui.listStatusPill.label).toBe("Paused – Awaiting Review");
  });

  it("3. completed + S11 → all completed, view_report", () => {
    const ui = deriveRunUiState({
      status: "completed",
      current_stage: "S11",
      pending_gate: null,
      reviews: [
        { gate: "H1", decision: "approved" },
        { gate: "H2", decision: "approved" },
        { gate: "H3", decision: "approved" },
        { gate: "H4", decision: "approved" },
        { gate: "H5", decision: "approved" },
      ],
    });
    expect(ui.uiStatus).toBe("completed");
    expect(ui.currentNodeId).toBe("S11");
    expect(ui.primaryCta).toBe("view_report");
    expect(ui.actionRequired).toBe(false);
    expect(ui.pipelineNodes.every((n) => n.state === "completed" || n.state === "approved")).toBe(
      true,
    );
    expect(ui.pipelineNodes.find((n) => n.id === "H5")?.state).toBe("approved");
  });

  it("4. failed + H2_rejected → rejected at H2", () => {
    const ui = deriveRunUiState({
      status: "failed",
      current_stage: "H2_rejected",
      pending_gate: null,
      reviews: [
        { gate: "H1", decision: "approved" },
        { gate: "H2", decision: "rejected" },
      ],
    });
    expect(ui.uiStatus).toBe("rejected");
    expect(ui.currentNodeId).toBe("H2");
    expect(ui.runHealth).toBe("failed");
    expect(ui.pipelineNodes.find((n) => n.id === "H2")?.state).toBe("failed");
    expect(ui.pipelineNodes.find((n) => n.id === "S3")?.state).toBe("completed");
    expect(ui.pipelineNodes.find((n) => n.id === "S5")?.state).toBe("pending");
    expect(ui.listStatusPill.key).toBe("rejected");
  });

  it("5. running + S1 → current S1", () => {
    const ui = deriveRunUiState({
      status: "running",
      current_stage: "S1",
    });
    expect(ui.uiStatus).toBe("running");
    expect(ui.currentNodeId).toBe("S1");
    expect(ui.pipelineNodes.find((n) => n.id === "S1")?.state).toBe("current");
    expect(ui.pipelineNodes.find((n) => n.id === "S2")?.state).toBe("pending");
    expect(ui.stopRunAvailable).toBe(false);
    expect(ui.shareAction).toBe("copy_url");
  });

  it("6. paused + H1_pending → awaiting H1", () => {
    const ui = deriveRunUiState({
      status: "paused",
      current_stage: "H1_pending",
      pending_gate: "H1",
      artifacts: [
        { type: "s1_normalized_requirement", version: 1 },
        { type: "s2_ambiguity_analysis", version: 1 },
      ],
    });
    expect(ui.uiStatus).toBe("awaiting_review");
    expect(ui.currentNodeId).toBe("H1");
    expect(ui.primaryCta).toBe("open_review");
    expect(ui.pipelineNodes.find((n) => n.id === "S1")?.state).toBe("completed");
    expect(ui.pipelineNodes.find((n) => n.id === "S2")?.state).toBe("completed");
  });

  it("7. running + S6 after H3 approve → Execute current", () => {
    const ui = deriveRunUiState({
      status: "running",
      current_stage: "S6",
      reviews: [
        { gate: "H1", decision: "approved" },
        { gate: "H2", decision: "approved" },
        { gate: "H3", decision: "approved" },
      ],
    });
    expect(ui.uiStatus).toBe("running");
    expect(ui.currentNodeId).toBe("S6");
    expect(ui.pipelineNodes.find((n) => n.id === "H3")?.state).toBe("approved");
    expect(ui.pipelineNodes.find((n) => n.id === "S6")?.state).toBe("current");
    expect(ui.pipelineNodes.find((n) => n.id === "H4")?.state).toBe("pending");
  });

  it("8. failed skill (non-reject) → failed health, not rejected pill", () => {
    const ui = deriveRunUiState({
      status: "failed",
      current_stage: "S7",
      pending_gate: null,
    });
    expect(ui.uiStatus).toBe("failed");
    expect(ui.currentNodeId).toBe("S7");
    expect(ui.listStatusPill.key).toBe("failed");
    expect(ui.listStatusPill.label).toBe("Failed");
    expect(ui.runHealth).toBe("failed");
  });

  it("9. H5 pending → release review action required", () => {
    const ui = deriveRunUiState({
      status: "paused",
      current_stage: "H5_pending",
      pending_gate: "H5",
    });
    expect(ui.actionGate).toBe("H5");
    expect(ui.currentLabel).toBe("H5 — Release Review");
    expect(ui.pipelineNodes.find((n) => n.id === "S11")?.state).toBe("pending");
  });

  it("10. cancelled → cancelled pill", () => {
    const ui = deriveRunUiState({
      status: "cancelled",
      current_stage: "S3",
    });
    expect(ui.uiStatus).toBe("cancelled");
    expect(ui.listStatusPill.key).toBe("cancelled");
  });

  it("running S1 is running with progressMessage, not revising", () => {
    const ui = deriveRunUiState({
      status: "running",
      current_stage: "S1",
      reviews: [{ gate: "H1", decision: "changes_requested" }],
    });
    expect(ui.uiStatus).toBe("running");
    expect(ui.currentNodeId).toBe("S1");
    expect(ui.progressMessage).toBe("Normalizing the requirement…");
  });

  it("running S2 exposes analyzing progressMessage", () => {
    const ui = deriveRunUiState({
      status: "running",
      current_stage: "S2",
      artifacts: [{ type: "s1_normalized_requirement" }],
    });
    expect(ui.uiStatus).toBe("running");
    expect(ui.currentNodeId).toBe("S2");
    expect(ui.progressMessage).toBe("Analyzing ambiguities…");
  });

  it("H3_revising is revising only from explicit stage", () => {
    const ui = deriveRunUiState({
      status: "running",
      current_stage: "H3_revising",
    });
    expect(ui.uiStatus).toBe("revising");
    expect(ui.progressMessage).toBe("Revising the prior phase, then this gate will reopen.");
  });

  it("paused H1 has no progressMessage", () => {
    const ui = deriveRunUiState({
      status: "paused",
      current_stage: "H1_pending",
      pending_gate: "H1",
    });
    expect(ui.uiStatus).toBe("awaiting_review");
    expect(ui.progressMessage).toBeNull();
  });
});

describe("pollFreshness", () => {
  it("is live when last success is under 5s and no failures", () => {
    expect(pollFreshness({ lastSuccessAt: 10_000, consecutiveFailures: 0, now: 12_000 })).toBe(
      "live",
    );
  });

  it("is updating between 5s and 15s", () => {
    expect(pollFreshness({ lastSuccessAt: 0, consecutiveFailures: 0, now: 8_000 })).toBe("updating");
  });

  it("is delayed after 15s or two failures", () => {
    expect(pollFreshness({ lastSuccessAt: 0, consecutiveFailures: 0, now: 16_000 })).toBe("delayed");
    expect(pollFreshness({ lastSuccessAt: 10_000, consecutiveFailures: 2, now: 10_500 })).toBe(
      "delayed",
    );
  });
});
