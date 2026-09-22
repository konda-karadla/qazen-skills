import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader, EmptyState } from "../components/ui/EmptyState";
import { ErrorBanner, LoadingSkeleton } from "../components/ui/AsyncState";
import { SearchInput } from "../components/ui/SearchInput";
import { Table, THead, Th, Td } from "../components/ui/Table";
import { StatusPill } from "../components/ui/StatusPill";
import { Card } from "../components/ui/Card";
import { api, formatWhen, shortRunId } from "../api/client";
import type { ExecutionListItem, RunListItem, ScriptListItem, TestCaseListItem } from "../api/types";
import { TraceabilityStrip, buildTraceSteps } from "../components/traceability/TraceabilityStrip";

type EvidenceItem = {
  storage_uri?: string;
  artifact_type?: string;
  test_case_id?: string;
  [key: string]: unknown;
};

function asEvidenceList(manifest: unknown): EvidenceItem[] {
  if (Array.isArray(manifest)) return manifest as EvidenceItem[];
  if (manifest && typeof manifest === "object" && Array.isArray((manifest as { items?: unknown }).items)) {
    return (manifest as { items: EvidenceItem[] }).items;
  }
  return [];
}

export function ExecutionsPage() {
  const [params, setParams] = useSearchParams();
  const runFilter = params.get("run") || "";
  const [q, setQ] = useState("");
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [items, setItems] = useState<ExecutionListItem[]>([]);
  const [tcByKey, setTcByKey] = useState<Record<string, TestCaseListItem>>({});
  const [scriptByKey, setScriptByKey] = useState<Record<string, ScriptListItem>>({});
  const [selected, setSelected] = useState<ExecutionListItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [exs, runList, tcs, scripts] = await Promise.all([
          api.listExecutions({ limit: 200, runId: runFilter || undefined }),
          api.listRuns({ limit: 50 }),
          api.listTestCases({ limit: 200, runId: runFilter || undefined }),
          api.listScripts({ limit: 200, runId: runFilter || undefined }),
        ]);
        if (cancelled) return;
        setItems(exs.executions);
        setRuns(runList.runs);
        const tcMap: Record<string, TestCaseListItem> = {};
        for (const tc of tcs.test_cases) tcMap[`${tc.run_id}:${tc.test_case_id}`] = tc;
        setTcByKey(tcMap);
        const sMap: Record<string, ScriptListItem> = {};
        for (const s of scripts.scripts) {
          if (s.run_id && s.test_case_id) sMap[`${s.run_id}:${s.test_case_id}`] = s;
        }
        setScriptByKey(sMap);
        setSelected((prev) => {
          if (!prev) return exs.executions[0] ?? null;
          return exs.executions.find((x) => x.execution_id === prev.execution_id) ?? exs.executions[0] ?? null;
        });
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load executions");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [runFilter, reloadKey]);

  const filtered = useMemo(() => {
    if (!q.trim()) return items;
    const needle = q.trim().toLowerCase();
    return items.filter((ex) =>
      `${ex.test_case_id} ${ex.run_id} ${ex.status} ${ex.classification ?? ""} ${ex.correlation_id ?? ""}`
        .toLowerCase()
        .includes(needle),
    );
  }, [items, q]);

  const linkedTc =
    selected?.run_id && selected.test_case_id
      ? tcByKey[`${selected.run_id}:${selected.test_case_id}`]
      : undefined;
  const linkedScript =
    selected?.run_id && selected.test_case_id
      ? scriptByKey[`${selected.run_id}:${selected.test_case_id}`]
      : undefined;
  const evidence = selected ? asEvidenceList(selected.evidence_manifest) : [];

  const trace = selected
    ? buildTraceSteps({
        runId: selected.run_id,
        requirementId: linkedTc?.source_requirement_id,
        obligation: linkedTc?.obligation,
        testCaseId: selected.test_case_id,
        scriptFile: linkedScript?.file_name,
        executionStatus: selected.status,
        highlight: "execution",
      })
    : [];

  return (
    <div>
      <PageHeader
        title="Executions"
        description="Playwright results with failure classification and evidence URIs when present."
      />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="max-w-sm flex-1">
          <SearchInput value={q} onChange={setQ} placeholder="Search executions…" />
        </div>
        <label className="flex items-center gap-2 text-sm text-muted">
          Run
          <select
            className="rounded-md border border-border bg-surface px-2.5 py-1.5 text-sm text-ink"
            value={runFilter}
            onChange={(e) => {
              const next = new URLSearchParams(params);
              if (e.target.value) next.set("run", e.target.value);
              else next.delete("run");
              setParams(next);
            }}
          >
            <option value="">All runs</option>
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {shortRunId(r.run_id)} · {r.status}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error ? <ErrorBanner message={error} onRetry={() => setReloadKey((k) => k + 1)} /> : null}
      {loading ? <LoadingSkeleton rows={4} label="Loading executions…" /> : null}

      {selected ? (
        <div className="mb-4 grid gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-2" title="Selected chain">
            <TraceabilityStrip steps={trace} />
          </Card>
          <Card title="Evidence">
            {evidence.length === 0 ? (
              <p className="text-sm text-muted">No evidence URIs on this execution.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {evidence.map((ev, i) => (
                  <li key={`${ev.storage_uri ?? i}`} className="rounded-md border border-border bg-canvas px-2.5 py-2">
                    <p className="text-xs font-medium text-ink">{ev.artifact_type || "artifact"}</p>
                    <p className="mt-0.5 break-all font-mono text-[11px] text-muted">
                      {ev.storage_uri || "—"}
                    </p>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-3 text-xs text-muted">
              Confidence scores are not stored on execution rows in v1 — classification is shown when S7 sets it.
            </p>
          </Card>
        </div>
      ) : null}

      {!loading && filtered.length === 0 ? (
        <EmptyState title="No executions" description="Results appear after S6." />
      ) : filtered.length > 0 ? (
        <Table>
          <THead>
            <tr>
              <Th>Test Case</Th>
              <Th>Run</Th>
              <Th>Status</Th>
              <Th>Classification</Th>
              <Th>Retries</Th>
              <Th>Correlation</Th>
              <Th>Created</Th>
            </tr>
          </THead>
          <tbody className="divide-y divide-border">
            {filtered.map((ex) => {
              const active = selected?.execution_id === ex.execution_id;
              const tone =
                ex.status === "pass" ? "success" : ex.status === "fail" ? "danger" : "muted";
              return (
                <tr
                  key={ex.execution_id}
                  className={`cursor-pointer hover:bg-canvas/80 ${active ? "bg-primary-soft/40" : ""}`}
                  onClick={() => setSelected(ex)}
                >
                  <Td className="font-mono text-xs">{ex.test_case_id}</Td>
                  <Td>
                    <Link
                      className="font-mono text-xs text-primary hover:underline"
                      to={`/runs/${ex.run_id}`}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {shortRunId(ex.run_id)}
                    </Link>
                  </Td>
                  <Td>
                    <StatusPill tone={tone}>{ex.status}</StatusPill>
                  </Td>
                  <Td className="text-xs">{ex.classification ?? "—"}</Td>
                  <Td className="text-xs">{ex.retry_attempts ?? 0}</Td>
                  <Td className="font-mono text-xs text-muted">{ex.correlation_id ?? "—"}</Td>
                  <Td className="text-xs text-muted">{formatWhen(ex.created_at)}</Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      ) : null}
    </div>
  );
}
