import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { shortRunId } from "../../api/client";

export type TraceStepStatus = "present" | "missing" | "current";

export interface TraceStep {
  id: string;
  label: string;
  value?: string | null;
  href?: string | null;
  status?: TraceStepStatus;
}

/** Requirement → Obligation → Test Case → Automation → Execution */
export function TraceabilityStrip({
  steps,
  title = "Traceability",
}: {
  steps: TraceStep[];
  title?: string;
}) {
  return (
    <div className="rounded-md border border-border bg-canvas px-3 py-3">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted">{title}</p>
      <ol className="flex flex-wrap items-stretch gap-1">
        {steps.map((step, idx) => {
          const status = step.status ?? (step.value ? "present" : "missing");
          const tone =
            status === "current"
              ? "border-primary bg-primary-soft text-primary"
              : status === "present"
                ? "border-border bg-surface text-ink"
                : "border-dashed border-border bg-surface/60 text-muted";
          return (
            <li key={step.id} className="flex min-w-0 items-center gap-1">
              <div className={`min-w-[7.5rem] max-w-[14rem] rounded-md border px-2.5 py-2 ${tone}`}>
                <p className="text-[10px] font-medium uppercase tracking-wide opacity-70">{step.label}</p>
                {step.href && step.value ? (
                  <Link className="mt-0.5 block truncate text-xs font-medium text-primary hover:underline" to={step.href}>
                    {step.value}
                  </Link>
                ) : (
                  <p className="mt-0.5 truncate text-xs font-medium" title={step.value ?? undefined}>
                    {step.value || "—"}
                  </p>
                )}
              </div>
              {idx < steps.length - 1 ? (
                <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted" aria-hidden />
              ) : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function buildTraceSteps(input: {
  runId?: string | null;
  requirementId?: string | null;
  obligation?: string | null;
  testCaseId?: string | null;
  scriptFile?: string | null;
  executionStatus?: string | null;
  highlight?: "requirement" | "obligation" | "test_case" | "automation" | "execution";
}): TraceStep[] {
  const runHref = input.runId ? `/runs/${input.runId}` : null;
  const req = input.requirementId || null;
  const obl = input.obligation
    ? input.obligation.length > 48
      ? `${input.obligation.slice(0, 48)}…`
      : input.obligation
    : null;
  return [
    {
      id: "requirement",
      label: "Requirement",
      value: req,
      href: runHref,
      status: input.highlight === "requirement" ? "current" : req ? "present" : "missing",
    },
    {
      id: "obligation",
      label: "Obligation / AC",
      value: obl,
      status: input.highlight === "obligation" ? "current" : obl ? "present" : "missing",
    },
    {
      id: "test_case",
      label: "Test Case",
      value: input.testCaseId,
      href: runHref,
      status: input.highlight === "test_case" ? "current" : input.testCaseId ? "present" : "missing",
    },
    {
      id: "automation",
      label: "Automation",
      value: input.scriptFile,
      href: runHref,
      status: input.highlight === "automation" ? "current" : input.scriptFile ? "present" : "missing",
    },
    {
      id: "execution",
      label: "Execution",
      value: input.executionStatus
        ? input.executionStatus
        : input.runId
          ? `Run ${shortRunId(input.runId)}`
          : null,
      href: runHref,
      status: input.highlight === "execution" ? "current" : input.executionStatus ? "present" : "missing",
    },
  ];
}
