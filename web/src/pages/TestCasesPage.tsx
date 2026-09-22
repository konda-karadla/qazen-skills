import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader, EmptyState } from "../components/ui/EmptyState";
import { ErrorBanner, LoadingSkeleton } from "../components/ui/AsyncState";
import { SearchInput } from "../components/ui/SearchInput";
import { Table, THead, Th, Td } from "../components/ui/Table";
import { StatusPill } from "../components/ui/StatusPill";
import { Card } from "../components/ui/Card";
import { api, formatWhen, shortRunId } from "../api/client";
import type { RunListItem, TestCaseListItem } from "../api/types";
import { TraceabilityStrip, buildTraceSteps } from "../components/traceability/TraceabilityStrip";

export function TestCasesPage() {
  const [params, setParams] = useSearchParams();
  const runFilter = params.get("run") || "";
  const [q, setQ] = useState("");
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [items, setItems] = useState<TestCaseListItem[]>([]);
  const [scriptsByKey, setScriptsByKey] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<TestCaseListItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [tc, runList, scripts] = await Promise.all([
          api.listTestCases({ limit: 200, runId: runFilter || undefined }),
          api.listRuns({ limit: 50 }),
          api.listScripts({ limit: 200, runId: runFilter || undefined }),
        ]);
        if (cancelled) return;
        setItems(tc.test_cases);
        setRuns(runList.runs);
        const map: Record<string, string> = {};
        for (const s of scripts.scripts) {
          if (s.run_id && s.test_case_id && s.file_name) {
            map[`${s.run_id}:${s.test_case_id}`] = s.file_name;
          }
        }
        setScriptsByKey(map);
        setSelected((prev) => {
          if (!prev) return tc.test_cases[0] ?? null;
          return tc.test_cases.find((x) => x.test_case_id === prev.test_case_id && x.run_id === prev.run_id) ?? tc.test_cases[0] ?? null;
        });
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load test cases");
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
    return items.filter((tc) =>
      `${tc.test_case_id} ${tc.run_id} ${tc.obligation ?? ""} ${tc.source_requirement_id ?? ""} ${tc.layer}`
        .toLowerCase()
        .includes(needle),
    );
  }, [items, q]);

  const trace = selected
    ? buildTraceSteps({
        runId: selected.run_id,
        requirementId: selected.source_requirement_id,
        obligation: selected.obligation,
        testCaseId: selected.test_case_id,
        scriptFile: scriptsByKey[`${selected.run_id}:${selected.test_case_id}`],
        executionStatus: selected.last_execution_status,
        highlight: "test_case",
      })
    : [];

  return (
    <div>
      <PageHeader
        title="Test Cases"
        description="Requirement-linked test cases with obligation and execution status."
      />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="max-w-sm flex-1">
          <SearchInput value={q} onChange={setQ} placeholder="Search test cases…" />
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
      {loading ? <LoadingSkeleton rows={4} label="Loading test cases…" /> : null}

      {selected ? (
        <Card className="mb-4" title="Selected chain">
          <TraceabilityStrip steps={trace} />
        </Card>
      ) : null}

      {!loading && filtered.length === 0 ? (
        <EmptyState title="No test cases" description="Test cases appear after S3 for a run." />
      ) : filtered.length > 0 ? (
        <Table>
          <THead>
            <tr>
              <Th>ID</Th>
              <Th>Run</Th>
              <Th>Requirement</Th>
              <Th>Layer</Th>
              <Th>Obligation</Th>
              <Th>Version</Th>
              <Th>Last Result</Th>
              <Th>Created</Th>
            </tr>
          </THead>
          <tbody className="divide-y divide-border">
            {filtered.map((tc) => {
              const active = selected?.test_case_id === tc.test_case_id && selected?.run_id === tc.run_id;
              const tone =
                tc.last_execution_status === "pass"
                  ? "success"
                  : tc.last_execution_status === "fail"
                    ? "danger"
                    : "muted";
              return (
                <tr
                  key={`${tc.run_id}-${tc.test_case_id}-${tc.version}`}
                  className={`cursor-pointer hover:bg-canvas/80 ${active ? "bg-primary-soft/40" : ""}`}
                  onClick={() => setSelected(tc)}
                >
                  <Td className="font-mono text-xs">{tc.test_case_id}</Td>
                  <Td>
                    <Link className="font-mono text-xs text-primary hover:underline" to={`/runs/${tc.run_id}`} onClick={(e) => e.stopPropagation()}>
                      {shortRunId(tc.run_id)}
                    </Link>
                  </Td>
                  <Td className="text-xs">{tc.source_requirement_id || "—"}</Td>
                  <Td>{tc.layer}</Td>
                  <Td className="max-w-md truncate text-sm">{tc.obligation ?? "—"}</Td>
                  <Td>v{tc.version}</Td>
                  <Td>
                    {tc.last_execution_status ? (
                      <StatusPill tone={tone}>{tc.last_execution_status}</StatusPill>
                    ) : (
                      "—"
                    )}
                  </Td>
                  <Td className="text-xs text-muted">{formatWhen(tc.created_at)}</Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      ) : null}
    </div>
  );
}
