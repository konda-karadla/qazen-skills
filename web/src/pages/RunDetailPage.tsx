import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ExternalLink, RefreshCw, Share2, Square } from "lucide-react";
import { api, formatWhen, shortRunId, ApiError } from "../api/client";
import type {
  ArtifactListItem,
  ExecutionListItem,
  LineageNode,
  RunDetailResponse,
  ScriptListItem,
  TestCaseListItem,
  TimelineEvent,
} from "../api/types";
import type { RunUiState } from "../lib/runState";
import { formatUpdatedAgo, pollFreshness } from "../lib/runState";
import { Button } from "../components/ui/Button";
import { StatusPill } from "../components/ui/StatusPill";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorBanner, LoadingBlock } from "../components/ui/AsyncState";
import { JsonViewer } from "../components/ui/JsonViewer";
import { Tabs, TabPanel } from "../components/ui/Tabs";
import { Table, THead, Th, Td } from "../components/ui/Table";
import { PipelineTimeline } from "../components/pipeline/PipelineTimeline";
import { ArtifactsTable } from "../components/run/ArtifactsTable";
import { AuditTimeline } from "../components/run/AuditTimeline";
import { ArtifactLineage } from "../components/run/ArtifactLineage";
import { TraceabilityStrip, buildTraceSteps } from "../components/traceability/TraceabilityStrip";

const GATE_COPY: Record<string, string> = {
  H1: "Confirm the normalized requirement and ambiguity analysis before test generation.",
  H2: "Review generated test cases and test data for coverage and correctness.",
  H3: "Review the generated automation scripts to ensure they assert the right thing.",
  H4: "Review execution results, failure classifications, security findings, and reports.",
  H5: "Review the factual release summary and decide go / no-go. No AI recommendation is shown.",
};

function pillTone(ui: RunUiState): "success" | "primary" | "amber" | "danger" | "muted" {
  switch (ui.listStatusPill.key) {
    case "awaiting_review":
      return "amber";
    case "completed":
      return "success";
    case "rejected":
    case "failed":
      return "danger";
    case "in_progress":
      return "primary";
    default:
      return "muted";
  }
}

function healthTone(h: string): "success" | "amber" | "danger" {
  if (h === "blocked") return "amber";
  if (h === "failed") return "danger";
  return "success";
}

export function RunDetailPage() {
  const { runId = "" } = useParams();
  const [run, setRun] = useState<RunDetailResponse | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactListItem[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [lineage, setLineage] = useState<LineageNode[]>([]);
  const [testCases, setTestCases] = useState<TestCaseListItem[]>([]);
  const [scripts, setScripts] = useState<ScriptListItem[]>([]);
  const [executions, setExecutions] = useState<ExecutionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastSuccessAt, setLastSuccessAt] = useState<number | null>(null);
  const [pollFailures, setPollFailures] = useState(0);
  const [nowTick, setNowTick] = useState(() => Date.now());
  const [tab, setTab] = useState("artifacts");
  const [stageFilter, setStageFilter] = useState("All");
  const [viewer, setViewer] = useState<{ title: string; value: unknown } | null>(null);
  const [shareNote, setShareNote] = useState<string | null>(null);
  const [selectedTcId, setSelectedTcId] = useState<string | null>(null);

  const load = useCallback(async (opts?: { silent?: boolean }) => {
    if (!runId) return;
    if (!opts?.silent) {
      setLoading(true);
      setError(null);
    }
    try {
      const [detail, arts, tl, lin, tcs, scs, exs] = await Promise.all([
        api.getRun(runId),
        api.getArtifacts(runId),
        api.getTimeline(runId),
        api.getLineage(runId),
        api.getTestCases(runId),
        api.getScripts(runId),
        api.getExecutions(runId),
      ]);
      setRun(detail);
      setArtifacts(arts.artifacts);
      setTimeline(tl.events);
      setLineage(lin.nodes);
      setTestCases(tcs.test_cases);
      setScripts(scs.scripts);
      setExecutions(exs.executions);
      setLastSuccessAt(Date.now());
      setPollFailures(0);
      return detail;
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Failed to load run";
      setError(msg);
      if (opts?.silent) setPollFailures((n) => n + 1);
    } finally {
      if (!opts?.silent) setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    void load();
  }, [load]);

  const isWorking = run?.status === "running";

  useEffect(() => {
    if (!isWorking) return;
    const id = window.setInterval(() => {
      void load({ silent: true });
    }, 2000);
    return () => window.clearInterval(id);
  }, [isWorking, load]);

  useEffect(() => {
    if (!isWorking) return;
    const id = window.setInterval(() => setNowTick(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [isWorking]);

  const ui = run?.ui_state;

  const stats = useMemo(() => {
    if (!ui) return { completed: 0, running: 0, pending: 0 };
    let completed = 0;
    let running = 0;
    let pending = 0;
    for (const n of ui.pipelineNodes) {
      if (n.state === "completed" || n.state === "approved") completed += 1;
      else if (n.state === "current") running += 1;
      else if (n.state === "pending") pending += 1;
    }
    return { completed, running, pending };
  }, [ui]);

  const reviewNeeds = useMemo(() => {
    const models = artifacts.filter((a) => a.type === "s5_automation_model").length;
    return {
      scripts: scripts.length,
      testCases: testCases.length,
      models,
      requirement: 1,
    };
  }, [artifacts, scripts.length, testCases.length]);

  async function onShare() {
    const url = window.location.href;
    try {
      await navigator.clipboard.writeText(url);
      setShareNote("Run URL copied");
    } catch {
      setShareNote(url);
    }
    window.setTimeout(() => setShareNote(null), 2500);
  }

  async function onViewArtifact(a: ArtifactListItem) {
    try {
      const detail = await api.getArtifact(runId, a.artifact_id);
      setViewer({ title: `${a.name} (v${a.version})`, value: detail.content });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load artifact");
    }
  }

  function onSelectStage(id: string) {
    setTab("artifacts");
    setStageFilter(id);
  }

  if (!runId) {
    return <EmptyState title="Missing run id" />;
  }

  if (loading && !run) {
    return <LoadingBlock label="Loading run…" className="py-8" />;
  }

  if (error && !run) {
    return (
      <EmptyState
        title="Could not load run"
        description={error}
        actionLabel="Retry"
        onAction={() => void load()}
      />
    );
  }

  if (!run || !ui) return null;

  const freshness = isWorking
    ? pollFreshness({ lastSuccessAt, consecutiveFailures: pollFailures, now: nowTick })
    : null;
  const liveCue =
    freshness === "live" && lastSuccessAt
      ? `Live • ${formatUpdatedAgo(lastSuccessAt, nowTick)}`
      : freshness === "updating"
        ? "Updating…"
        : freshness === "delayed"
          ? "Connection delayed • Retrying..."
          : null;
  const pulseCurrent = freshness === "live" || freshness === "updating";
  const stageBody = ui.actionRequired
    ? (ui.actionGate && GATE_COPY[ui.actionGate]) ||
      "Pipeline stage details and artifacts are shown below."
    : ui.progressMessage || "Pipeline stage details and artifacts are shown below.";

  return (
    <div className="xl:grid xl:grid-cols-[minmax(0,1fr)_280px] xl:gap-5">
      <div className="min-w-0">
        <Link to="/runs" className="text-sm text-primary hover:underline">
          ← Back to Runs
        </Link>

        {ui.progressMessage ? (
          <div className="mt-3 rounded-md border border-primary/20 bg-primary-soft px-3 py-2 text-sm text-primary">
            <strong>In progress</strong> — {ui.progressMessage} This page updates automatically.
            Local models can take several minutes.
          </div>
        ) : ui.actionRequired ? (
          <div className="mt-3 rounded-md border border-amber-200 bg-amber-soft px-3 py-2 text-sm text-amber">
            <strong>Action Required</strong> — {ui.currentLabel}. Human approval is needed before the
            pipeline continues.
          </div>
        ) : null}

        <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-semibold text-ink" title={run.run_id}>
                Run {shortRunId(run.run_id)}
              </h1>
              <StatusPill tone={pillTone(ui)}>{ui.listStatusPill.label}</StatusPill>
              {liveCue ? (
                <span
                  className={`text-xs ${freshness === "delayed" ? "text-amber" : "text-muted"}`}
                >
                  {liveCue}
                </span>
              ) : null}
            </div>
            <p className="mt-1 max-w-3xl text-sm text-ink">
              {run.requirement_summary || "Summary appears after S1 finishes."}
            </p>
            <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
              <div>
                <dt className="inline">Created: </dt>
                <dd className="inline">{formatWhen(run.created_at)}</dd>
              </div>
              <div>
                <dt className="inline">Requirement ID: </dt>
                <dd className="inline font-mono">{run.requirement_id}</dd>
              </div>
              {run.branch ? (
                <div>
                  <dt className="inline">Branch: </dt>
                  <dd className="inline">{run.branch}</dd>
                </div>
              ) : null}
              {run.environment ? (
                <div>
                  <dt className="inline">Environment: </dt>
                  <dd className="inline">{run.environment}</dd>
                </div>
              ) : null}
              {run.base_url ? (
                <div>
                  <dt className="inline">Base URL: </dt>
                  <dd className="inline font-mono">{run.base_url}</dd>
                </div>
              ) : null}
              <div>
                <dt className="inline">Stage: </dt>
                <dd className="inline">{run.current_stage ?? "—"}</dd>
              </div>
            </dl>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" size="sm" aria-label="Refresh" onClick={() => void load()}>
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            </Button>
            <Button variant="primary" size="sm" onClick={() => void onShare()}>
              <Share2 className="h-3.5 w-3.5" /> Share
            </Button>
            <Button
              variant="outline-danger"
              size="sm"
              disabled={!ui.stopRunAvailable}
              title="Cancellation not available yet"
            >
              <Square className="h-3.5 w-3.5" /> Stop Run
            </Button>
          </div>
        </div>
        {shareNote ? <p className="mt-1 text-xs text-success">{shareNote}</p> : null}
        {error ? <ErrorBanner className="mt-2 mb-0" message={error} onRetry={() => void load()} /> : null}
        {run.last_skill_error ? (
          <div
            className={`mt-3 rounded-md border px-3 py-2 text-sm ${
              run.last_skill_error.is_quota_or_auth
                ? "border-amber-300 bg-amber-50 text-amber-950"
                : "border-danger/30 bg-danger/5 text-ink"
            }`}
            role="status"
          >
            <p className="font-medium">
              {run.last_skill_error.is_quota_or_auth
                ? "LLM quota or auth failed"
                : `Skill failure${run.last_skill_error.skill ? ` (${run.last_skill_error.skill})` : ""}`}
            </p>
            <p className="mt-1 text-xs leading-relaxed opacity-90">{run.last_skill_error.reason}</p>
            {run.last_skill_error.is_quota_or_auth ? (
              <p className="mt-2 text-xs">
                Update <code className="font-mono">OPENAI_API_KEY</code> / switch{" "}
                <code className="font-mono">LLM_PROFILE</code> in repo-root{" "}
                <code className="font-mono">.env</code>, restart gateway :8000, then start a new run. See{" "}
                <Link className="text-primary hover:underline" to="/settings">
                  Settings
                </Link>
                .
              </p>
            ) : null}
          </div>
        ) : null}

        <Card className="mt-5" title="Pipeline">
          <PipelineTimeline
            nodes={ui.pipelineNodes}
            onSelect={onSelectStage}
            selectedId={stageFilter === "All" ? ui.currentNodeId : stageFilter}
            pulseCurrent={pulseCurrent}
          />
        </Card>

        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <Card title="Current Stage">
            <p className="text-lg font-semibold text-ink">{ui.currentLabel}</p>
            <p className="mt-1 text-sm text-muted">{stageBody}</p>
            {ui.primaryCta === "open_review" && ui.actionGate ? (
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <Link to={`/runs/${runId}/review/${ui.actionGate}`}>
                  <Button>Open Review →</Button>
                </Link>
                <a
                  className="text-sm text-primary hover:underline"
                  href="/ui/"
                  onClick={(e) => {
                    e.preventDefault();
                    setTab("timeline");
                  }}
                >
                  View Instructions
                </a>
              </div>
            ) : null}
          </Card>

          <Card title="What needs your review?">
            {ui.actionRequired ? (
              <ul className="space-y-2 text-sm text-ink">
                <li>Generated Scripts — {reviewNeeds.scripts} files</li>
                <li>Test Cases — {reviewNeeds.testCases} cases</li>
                <li>Automation Model — {reviewNeeds.models} models</li>
                <li>Related Requirement — {reviewNeeds.requirement} requirement</li>
              </ul>
            ) : isWorking || ui.uiStatus === "revising" ? (
              <p className="text-sm text-muted">Pipeline is running — nothing to approve yet.</p>
            ) : (
              <p className="text-sm text-muted">No human review is pending for this run.</p>
            )}
          </Card>

          <Card title="Run Statistics">
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded-md bg-success-soft px-2 py-3">
                <p className="text-lg font-semibold text-success">{stats.completed}</p>
                <p className="text-[10px] text-muted">Completed</p>
              </div>
              <div className="rounded-md bg-primary-soft px-2 py-3">
                <p className="text-lg font-semibold text-primary">{stats.running}</p>
                <p className="text-[10px] text-muted">Current</p>
              </div>
              <div className="rounded-md bg-canvas px-2 py-3">
                <p className="text-lg font-semibold text-ink">{stats.pending}</p>
                <p className="text-[10px] text-muted">Pending</p>
              </div>
            </div>
            <div className="mt-3 space-y-1 text-xs text-muted">
              <p>
                Run Health:{" "}
                <StatusPill tone={healthTone(ui.runHealth)}>
                  {ui.runHealth === "on_track"
                    ? "On Track"
                    : ui.runHealth === "blocked"
                      ? "Action Required"
                      : "Failed"}
                </StatusPill>
              </p>
              <p>Started: {formatWhen(run.created_at)}</p>
              <p>Updated: {formatWhen(run.updated_at)}</p>
            </div>
          </Card>
        </div>

        <Card className="mt-4" title="Artifact lineage">
          <ArtifactLineage nodes={lineage} />
        </Card>

        <div className="mt-4 rounded-lg border border-border bg-surface p-4 shadow-sm">
          <Tabs
            active={tab}
            onChange={setTab}
            tabs={[
              { id: "artifacts", label: "Artifacts", count: artifacts.length },
              { id: "test-cases", label: "Test Cases", count: testCases.length },
              { id: "scripts", label: "Scripts", count: scripts.length },
              { id: "execution", label: "Execution", count: executions.length },
              { id: "reports", label: "Reports" },
              { id: "logs", label: "Logs" },
              { id: "timeline", label: "Timeline", count: timeline.length },
            ]}
          />

          <TabPanel active={tab} id="artifacts">
            <ArtifactsTable
              artifacts={artifacts}
              stageFilter={stageFilter}
              onStageFilterChange={setStageFilter}
              onView={(a) => void onViewArtifact(a)}
            />
          </TabPanel>

          <TabPanel active={tab} id="test-cases">
            {testCases.length === 0 ? (
              <EmptyState title="No test cases yet" description="Test cases appear after S3." />
            ) : (
              <div className="space-y-3">
                {(() => {
                  const selected =
                    testCases.find((tc) => tc.test_case_id === selectedTcId) ?? testCases[0];
                  const script = scripts.find((s) => s.test_case_id === selected.test_case_id);
                  const ex = executions.find((e) => e.test_case_id === selected.test_case_id);
                  return (
                    <TraceabilityStrip
                      steps={buildTraceSteps({
                        runId,
                        requirementId: selected.source_requirement_id,
                        obligation: selected.obligation,
                        testCaseId: selected.test_case_id,
                        scriptFile: script?.file_name,
                        executionStatus: ex?.status ?? selected.last_execution_status,
                        highlight: "test_case",
                      })}
                    />
                  );
                })()}
                <Table>
                  <THead>
                    <tr>
                      <Th>ID</Th>
                      <Th>Layer</Th>
                      <Th>Obligation</Th>
                      <Th>Version</Th>
                      <Th>Last Result</Th>
                    </tr>
                  </THead>
                  <tbody className="divide-y divide-border">
                    {testCases.map((tc) => (
                      <tr
                        key={`${tc.test_case_id}-${tc.version}`}
                        className={`cursor-pointer hover:bg-canvas/80 ${
                          (selectedTcId ?? testCases[0]?.test_case_id) === tc.test_case_id
                            ? "bg-primary-soft/40"
                            : ""
                        }`}
                        onClick={() => setSelectedTcId(tc.test_case_id)}
                      >
                        <Td className="font-mono text-xs">{tc.test_case_id}</Td>
                        <Td>{tc.layer}</Td>
                        <Td className="max-w-md truncate text-sm">{tc.obligation ?? "—"}</Td>
                        <Td>v{tc.version}</Td>
                        <Td>{tc.last_execution_status ?? "—"}</Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            )}
          </TabPanel>

          <TabPanel active={tab} id="scripts">
            {scripts.length === 0 ? (
              <EmptyState title="No scripts yet" description="Compiled Playwright scripts appear after S5." />
            ) : (
              <div className="space-y-3">
                {(() => {
                  const s = scripts[0];
                  const tc = testCases.find((t) => t.test_case_id === s.test_case_id);
                  const ex = executions.find((e) => e.test_case_id === s.test_case_id);
                  return (
                    <TraceabilityStrip
                      steps={buildTraceSteps({
                        runId,
                        requirementId: tc?.source_requirement_id,
                        obligation: tc?.obligation,
                        testCaseId: s.test_case_id,
                        scriptFile: s.file_name,
                        executionStatus: ex?.status ?? tc?.last_execution_status,
                        highlight: "automation",
                      })}
                    />
                  );
                })()}
                <Table>
                  <THead>
                    <tr>
                      <Th>File</Th>
                      <Th>Test Case</Th>
                      <Th>Framework</Th>
                      <Th>Version</Th>
                      <Th>Actions</Th>
                    </tr>
                  </THead>
                  <tbody className="divide-y divide-border">
                    {scripts.map((s, i) => (
                      <tr key={`${s.file_name}-${i}`}>
                        <Td className="font-mono text-xs">{s.file_name}</Td>
                        <Td>{s.test_case_id}</Td>
                        <Td>{s.framework}</Td>
                        <Td>v{s.version}</Td>
                        <Td>
                          {s.source ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                setViewer({ title: s.file_name, value: s.source })
                              }
                            >
                              View
                            </Button>
                          ) : (
                            "—"
                          )}
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            )}
          </TabPanel>

          <TabPanel active={tab} id="execution">
            {executions.length === 0 ? (
              <EmptyState title="No executions yet" description="Results appear after S6." />
            ) : (
              <div className="space-y-3">
                {(() => {
                  const ex = executions[0];
                  const tc = testCases.find((t) => t.test_case_id === ex.test_case_id);
                  const script = scripts.find((s) => s.test_case_id === ex.test_case_id);
                  return (
                    <TraceabilityStrip
                      steps={buildTraceSteps({
                        runId,
                        requirementId: tc?.source_requirement_id,
                        obligation: tc?.obligation,
                        testCaseId: ex.test_case_id,
                        scriptFile: script?.file_name,
                        executionStatus: ex.status,
                        highlight: "execution",
                      })}
                    />
                  );
                })()}
                <Table>
                  <THead>
                    <tr>
                      <Th>Test Case</Th>
                      <Th>Status</Th>
                      <Th>Classification</Th>
                      <Th>Created</Th>
                    </tr>
                  </THead>
                  <tbody className="divide-y divide-border">
                    {executions.map((ex) => (
                      <tr key={ex.execution_id}>
                        <Td className="font-mono text-xs">{ex.test_case_id}</Td>
                        <Td>{ex.status}</Td>
                        <Td className="text-xs">{ex.classification ?? "—"}</Td>
                        <Td className="text-xs text-muted">{formatWhen(ex.created_at)}</Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            )}
          </TabPanel>

          <TabPanel active={tab} id="reports">
            {(() => {
              const s9 = artifacts.find((a) => a.type === "s9_report");
              const al = artifacts.find((a) => a.type === "s9_allure_results");
              if (!s9 && !al) {
                return (
                  <EmptyState
                    title="No report artifacts yet"
                    description="S9 report / Allure results appear after reporting. Cross-run trends are not invented here."
                  />
                );
              }
              return (
                <div className="space-y-3 text-sm">
                  <p className="text-muted">
                    Current-run report artifacts only. Open the Reports page for metrics and summary.
                  </p>
                  <ul className="space-y-2">
                    {s9 ? (
                      <li className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                        <span className="font-mono text-xs">{s9.type} v{s9.version}</span>
                        <Button variant="ghost" size="sm" onClick={() => void onViewArtifact(s9)}>
                          View
                        </Button>
                      </li>
                    ) : null}
                    {al ? (
                      <li className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                        <span className="font-mono text-xs">{al.type} v{al.version}</span>
                        <Button variant="ghost" size="sm" onClick={() => void onViewArtifact(al)}>
                          View
                        </Button>
                      </li>
                    ) : null}
                  </ul>
                  <Link className="text-sm text-primary hover:underline" to={`/reports?run=${runId}`}>
                    Open Reports for this run →
                  </Link>
                </div>
              );
            })()}
          </TabPanel>

          <TabPanel active={tab} id="logs">
            <EmptyState
              title="No dedicated log stream"
              description="Use Timeline for stage/review audit events. Execution evidence is on the Execution tab."
            />
          </TabPanel>

          <TabPanel active={tab} id="timeline">
            <AuditTimeline events={timeline} />
          </TabPanel>
        </div>
      </div>

      <aside className="mt-5 space-y-4 xl:mt-0">
        <Card
          title="Requirement"
          action={
            <span className="text-[10px] font-medium uppercase text-muted">Read-only</span>
          }
        >
          <p className="text-sm text-ink whitespace-pre-wrap">
            {run.requirement_summary || "—"}
          </p>
          <dl className="mt-3 space-y-1 text-xs text-muted">
            <div>
              <dt className="inline font-medium text-ink">ID: </dt>
              <dd className="inline font-mono">{run.requirement_id}</dd>
            </div>
            {run.environment ? (
              <div>
                <dt className="inline font-medium text-ink">Environment: </dt>
                <dd className="inline">{run.environment}</dd>
              </div>
            ) : null}
            {run.base_url ? (
              <div>
                <dt className="inline font-medium text-ink">Base URL: </dt>
                <dd className="inline font-mono break-all">{run.base_url}</dd>
              </div>
            ) : null}
            {run.branch ? (
              <div>
                <dt className="inline font-medium text-ink">Branch: </dt>
                <dd className="inline">{run.branch}</dd>
              </div>
            ) : null}
          </dl>
        </Card>

        <Card title="Quick Actions">
          <ul className="space-y-2 text-sm">
            {ui.actionGate ? (
              <li>
                <Link className="text-primary hover:underline" to={`/runs/${runId}/review/${ui.actionGate}`}>
                  Open {ui.actionGate} Review
                </Link>
              </li>
            ) : null}
            <li>
              <button type="button" className="text-primary hover:underline" onClick={() => setTab("timeline")}>
                Open audit timeline
              </button>
            </li>
            <li>
              <button type="button" className="text-primary hover:underline" onClick={() => setTab("artifacts")}>
                Browse artifacts
              </button>
            </li>
            <li>
              <a className="inline-flex items-center gap-1 text-primary hover:underline" href="/docs" target="_blank" rel="noreferrer">
                API docs <ExternalLink className="h-3 w-3" />
              </a>
            </li>
          </ul>
        </Card>

        <Card title="Helpful Links">
          <ul className="space-y-2 text-sm text-primary">
            <li>
              <a className="hover:underline" href="/ui/" onClick={(e) => e.preventDefault()}>
                AGENT_INSTRUCTIONS.md
              </a>
              <span className="ml-1 text-xs text-muted">(repo)</span>
            </li>
            <li>
              <span className="text-muted">Runbook — local README</span>
            </li>
          </ul>
        </Card>
      </aside>

      {viewer ? (
        <JsonViewer title={viewer.title} value={viewer.value} onClose={() => setViewer(null)} />
      ) : null}
    </div>
  );
}
