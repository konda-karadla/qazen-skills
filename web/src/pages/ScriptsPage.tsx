import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader, EmptyState } from "../components/ui/EmptyState";
import { ErrorBanner, LoadingSkeleton } from "../components/ui/AsyncState";
import { SearchInput } from "../components/ui/SearchInput";
import { Table, THead, Th, Td } from "../components/ui/Table";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { JsonViewer } from "../components/ui/JsonViewer";
import { api, formatWhen, shortRunId } from "../api/client";
import type { RunListItem, ScriptListItem, TestCaseListItem } from "../api/types";
import { TraceabilityStrip, buildTraceSteps } from "../components/traceability/TraceabilityStrip";

export function ScriptsPage() {
  const [params, setParams] = useSearchParams();
  const runFilter = params.get("run") || "";
  const [q, setQ] = useState("");
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [items, setItems] = useState<ScriptListItem[]>([]);
  const [tcByKey, setTcByKey] = useState<Record<string, TestCaseListItem>>({});
  const [selected, setSelected] = useState<ScriptListItem | null>(null);
  const [viewer, setViewer] = useState<{ title: string; value: unknown } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [scripts, runList, tcs] = await Promise.all([
          api.listScripts({ limit: 200, runId: runFilter || undefined }),
          api.listRuns({ limit: 50 }),
          api.listTestCases({ limit: 200, runId: runFilter || undefined }),
        ]);
        if (cancelled) return;
        setItems(scripts.scripts);
        setRuns(runList.runs);
        const map: Record<string, TestCaseListItem> = {};
        for (const tc of tcs.test_cases) {
          map[`${tc.run_id}:${tc.test_case_id}`] = tc;
        }
        setTcByKey(map);
        setSelected((prev) => {
          if (!prev) return scripts.scripts[0] ?? null;
          return (
            scripts.scripts.find(
              (x) => x.file_name === prev.file_name && x.run_id === prev.run_id && x.test_case_id === prev.test_case_id,
            ) ??
            scripts.scripts[0] ??
            null
          );
        });
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load scripts");
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
    return items.filter((s) =>
      `${s.file_name} ${s.test_case_id} ${s.run_id ?? ""} ${s.framework}`.toLowerCase().includes(needle),
    );
  }, [items, q]);

  const linkedTc = selected?.run_id && selected.test_case_id
    ? tcByKey[`${selected.run_id}:${selected.test_case_id}`]
    : undefined;

  const trace = selected
    ? buildTraceSteps({
        runId: selected.run_id,
        requirementId: linkedTc?.source_requirement_id,
        obligation: linkedTc?.obligation,
        testCaseId: selected.test_case_id,
        scriptFile: selected.file_name,
        executionStatus: linkedTc?.last_execution_status,
        highlight: "automation",
      })
    : [];

  return (
    <div>
      <PageHeader
        title="Scripts"
        description="Compiled Playwright specs linked to automation model and test cases."
      />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="max-w-sm flex-1">
          <SearchInput value={q} onChange={setQ} placeholder="Search scripts…" />
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
      {loading ? <LoadingSkeleton rows={4} label="Loading scripts…" /> : null}

      {selected ? (
        <Card className="mb-4" title="Selected chain">
          <TraceabilityStrip steps={trace} />
          <p className="mt-2 text-xs text-muted">
            Model → Compile: Playwright Test runner (not MCP). Spec version v{selected.version}.
          </p>
        </Card>
      ) : null}

      {!loading && filtered.length === 0 ? (
        <EmptyState title="No scripts" description="Compiled Playwright scripts appear after S5 / Compile." />
      ) : filtered.length > 0 ? (
        <Table>
          <THead>
            <tr>
              <Th>File</Th>
              <Th>Test Case</Th>
              <Th>Run</Th>
              <Th>Framework</Th>
              <Th>Version</Th>
              <Th>Created</Th>
              <Th>Actions</Th>
            </tr>
          </THead>
          <tbody className="divide-y divide-border">
            {filtered.map((s, i) => {
              const active =
                selected?.file_name === s.file_name &&
                selected?.run_id === s.run_id &&
                selected?.test_case_id === s.test_case_id;
              return (
                <tr
                  key={`${s.run_id}-${s.file_name}-${i}`}
                  className={`cursor-pointer hover:bg-canvas/80 ${active ? "bg-primary-soft/40" : ""}`}
                  onClick={() => setSelected(s)}
                >
                  <Td className="font-mono text-xs">{s.file_name}</Td>
                  <Td className="font-mono text-xs">{s.test_case_id}</Td>
                  <Td>
                    {s.run_id ? (
                      <Link
                        className="font-mono text-xs text-primary hover:underline"
                        to={`/runs/${s.run_id}`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        {shortRunId(s.run_id)}
                      </Link>
                    ) : (
                      "—"
                    )}
                  </Td>
                  <Td>{s.framework}</Td>
                  <Td>v{s.version}</Td>
                  <Td className="text-xs text-muted">{formatWhen(s.created_at)}</Td>
                  <Td>
                    {s.source ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setViewer({ title: s.file_name, value: s.source });
                        }}
                      >
                        View
                      </Button>
                    ) : (
                      "—"
                    )}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      ) : null}

      {viewer ? (
        <JsonViewer title={viewer.title} value={viewer.value} onClose={() => setViewer(null)} />
      ) : null}
    </div>
  );
}
