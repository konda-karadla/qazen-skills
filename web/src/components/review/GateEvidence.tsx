/** Compact JSON / structured evidence display for review gates. */

export function EvidenceBlock({ title, value }: { title: string; value: unknown }) {
  const text =
    value == null
      ? "—"
      : typeof value === "string"
        ? value
        : JSON.stringify(value, null, 2);

  return (
    <section className="rounded-md border border-border bg-canvas">
      <header className="border-b border-border px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted">
        {title}
      </header>
      <pre className="max-h-80 overflow-auto p-3 font-mono text-xs leading-relaxed text-ink whitespace-pre-wrap">
        {text}
      </pre>
    </section>
  );
}

export function CodeBlock({ title, source }: { title: string; source: string }) {
  return (
    <section className="rounded-md border border-border overflow-hidden">
      <header className="border-b border-border bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-200">
        {title}
      </header>
      <pre className="max-h-[28rem] overflow-auto bg-slate-950 p-3 font-mono text-xs leading-relaxed text-slate-100 whitespace-pre">
        {source}
      </pre>
    </section>
  );
}

function asRecord(v: unknown): Record<string, unknown> | null {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
}

export function H1Evidence({ evidence }: { evidence: Record<string, unknown> }) {
  const s1 = evidence.s1_normalized_requirement;
  const s2 = evidence.s2_ambiguity_analysis;
  const s2rec = asRecord(s2);
  const statements = Array.isArray(s2rec?.statements) ? s2rec.statements : null;
  const ambiguities = Array.isArray(s2rec?.ambiguities) ? s2rec.ambiguities : null;

  return (
    <div className="space-y-4">
      <EvidenceBlock title="S1 — Normalized requirement" value={s1} />
      {statements ? (
        <section className="rounded-md border border-border p-3">
          <h3 className="text-xs font-semibold uppercase text-muted">Statement classifications</h3>
          <ul className="mt-2 space-y-2">
            {statements.map((s, i) => {
              const row = asRecord(s) ?? {};
              const tag = String(row.tag ?? row.classification ?? "—");
              return (
                <li key={i} className="rounded border border-border bg-canvas px-3 py-2 text-sm">
                  <span className="mr-2 rounded bg-primary-soft px-1.5 py-0.5 text-[10px] font-bold uppercase text-primary">
                    {tag}
                  </span>
                  {String(row.text ?? row.statement ?? JSON.stringify(row))}
                </li>
              );
            })}
          </ul>
        </section>
      ) : (
        <EvidenceBlock title="S2 — Ambiguity analysis" value={s2} />
      )}
      {ambiguities && ambiguities.length > 0 ? (
        <section className="rounded-md border border-amber-200 bg-amber-soft p-3">
          <h3 className="text-xs font-semibold uppercase text-amber">Ambiguities</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink">
            {ambiguities.map((a, i) => (
              <li key={i}>{typeof a === "string" ? a : JSON.stringify(a)}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

export function H2Evidence({ evidence }: { evidence: Record<string, unknown> }) {
  const s3 = asRecord(evidence.s3_test_cases);
  const s4 = asRecord(evidence.s4_test_data);
  const cases = Array.isArray(s3?.test_cases) ? s3.test_cases : null;
  const datasets = Array.isArray(s4?.datasets) ? s4.datasets : null;
  const emptyCases = cases != null && cases.length === 0;
  const emptyDatasets = datasets != null && datasets.length === 0;

  return (
    <div className="space-y-4">
      {emptyCases || emptyDatasets ? (
        <div className="rounded-md border border-amber-200 bg-amber-soft px-3 py-2 text-sm text-ink">
          <p className="font-medium text-amber">
            Empty S3/S4 output — do not Approve yet.
          </p>
          <p className="mt-1 text-xs text-muted">
            {emptyCases ? "test_cases is empty. " : ""}
            {emptyDatasets ? "datasets is empty. " : ""}
            Use <strong>Request Changes</strong> and ask for concrete cases (e.g. valid + invalid
            login) with no empty arrays. New schema rules reject empty arrays on future S3/S4
            invokes.
          </p>
        </div>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <EvidenceBlock title="S3 — Test cases" value={evidence.s3_test_cases} />
        <EvidenceBlock title="S4 — Test data" value={evidence.s4_test_data} />
      </div>
    </div>
  );
}

export function H3Evidence({ evidence }: { evidence: Record<string, unknown> }) {
  const model = evidence.s5_automation_model;
  const compiled = asRecord(evidence.s5_compiled_playwright);
  const compiledScripts = Array.isArray(evidence.compiled_scripts)
    ? evidence.compiled_scripts
    : null;
  const automationModels = Array.isArray(evidence.automation_models)
    ? evidence.automation_models
    : null;
  const source = typeof compiled?.source === "string" ? compiled.source : null;
  const fileName = typeof compiled?.file_name === "string" ? compiled.file_name : "compiled.spec.ts";
  const testCaseId = compiled?.test_case_id;
  const modelRec = asRecord(model);
  const cases = Array.isArray(modelRec?.automation_models)
    ? modelRec.automation_models
    : Array.isArray(modelRec?.models)
      ? modelRec.models
      : null;

  const multiScripts =
    compiledScripts
      ?.map((row) => asRecord(row))
      .filter((row): row is Record<string, unknown> => row != null)
      .filter((row) => typeof row.source === "string" && row.source.length > 0) ?? [];

  const multiModels =
    automationModels
      ?.map((row) => asRecord(row))
      .filter((row): row is Record<string, unknown> => row != null) ?? [];

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-md border border-border p-3">
          <h3 className="text-xs font-semibold uppercase text-muted">Test case / expected behavior</h3>
          {multiModels.length > 1 ? (
            <ul className="mt-2 space-y-1 text-sm text-ink">
              {multiModels.map((row, i) => (
                <li key={i} className="font-mono text-xs">
                  {String(row.test_case_id ?? row.script_id ?? `model-${i + 1}`)}
                  {row.version != null ? ` · model v${String(row.version)}` : ""}
                </li>
              ))}
            </ul>
          ) : testCaseId ? (
            <p className="mt-2 font-mono text-sm text-ink">{String(testCaseId)}</p>
          ) : null}
          {multiScripts.length > 1 ? (
            <ul className="mt-2 space-y-1 text-sm text-ink">
              {multiScripts.map((row, i) => (
                <li key={i} className="font-mono text-xs text-muted">
                  spec {String(row.file_name ?? `spec-${i + 1}`)}
                  {row.version != null ? ` · v${String(row.version)}` : ""}
                </li>
              ))}
            </ul>
          ) : cases && cases[0] ? (
            <pre className="mt-2 max-h-64 overflow-auto font-mono text-xs text-ink whitespace-pre-wrap">
              {JSON.stringify(cases[0], null, 2)}
            </pre>
          ) : multiModels.length === 0 ? (
            <p className="mt-2 text-sm text-muted">
              Linked test-case detail is in the automation model below.
            </p>
          ) : null}
        </section>
        {multiModels.length > 1 ? (
          <section className="rounded-md border border-border p-3">
            <h3 className="text-xs font-semibold uppercase text-muted">
              S5 — Automation models ({multiModels.length})
            </h3>
            <p className="mt-1 text-xs text-muted">
              Each S5 invoke covers one test case; request-changes appends another. Newest per
              test_case_id is shown.
            </p>
          </section>
        ) : (
          <EvidenceBlock title="S5 — Automation model (latest invoke)" value={model} />
        )}
      </div>
      {multiModels.length > 1
        ? multiModels.map((row, i) => (
            <EvidenceBlock
              key={`${String(row.test_case_id ?? i)}-v${String(row.version ?? i)}`}
              title={`S5 — ${String(row.test_case_id ?? row.script_id ?? `model-${i + 1}`)} (v${String(row.version ?? "?")})`}
              value={row.model ?? row}
            />
          ))
        : null}
      {multiScripts.length > 0 ? (
        <div className="space-y-3">
          <p className="text-xs text-muted">
            Compiled Playwright specs on this run ({multiScripts.length}). S6 executes every file under
            generated/&lt;run_id&gt;/.
          </p>
          {multiScripts.map((row, i) => (
            <CodeBlock
              key={`${String(row.file_name ?? i)}-v${String(row.version ?? i)}`}
              title={`Compiled Playwright — ${String(row.file_name ?? `spec-${i + 1}`)}${
                row.test_case_id ? ` (${String(row.test_case_id)})` : ""
              }`}
              source={String(row.source)}
            />
          ))}
        </div>
      ) : source ? (
        <CodeBlock title={`Compiled Playwright — ${fileName}`} source={source} />
      ) : (
        <EvidenceBlock title="Compiled Playwright" value={evidence.s5_compiled_playwright} />
      )}
    </div>
  );
}

export function H4Evidence({ evidence }: { evidence: Record<string, unknown> }) {
  const report = asRecord(evidence.s9_report);
  const summary =
    typeof report?.human_readable_summary === "string" ? report.human_readable_summary : null;
  return (
    <div className="space-y-4">
      {summary ? (
        <section className="rounded-md border border-border bg-primary-soft p-4 text-sm text-ink whitespace-pre-wrap">
          {summary}
        </section>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <EvidenceBlock title="S6 — Execution" value={evidence.s6_execution_result} />
        <EvidenceBlock title="S7 — Failure classification" value={evidence.s7_classification} />
        <EvidenceBlock title="S8 — Security / boundary" value={evidence.s8_boundary_scan} />
        <EvidenceBlock title="S9 — Report" value={evidence.s9_report} />
      </div>
    </div>
  );
}

export function H5Evidence({ evidence }: { evidence: Record<string, unknown> }) {
  const summary = asRecord(evidence.s10_release_summary);
  const narrative =
    typeof summary?.factual_narrative === "string" ? summary.factual_narrative : null;
  return (
    <div className="space-y-4">
      <p className="rounded-md border border-border bg-canvas px-3 py-2 text-xs text-muted">
        S10 presents facts only. No ship/hold recommendation is shown — the human decides go / no-go.
      </p>
      {narrative ? (
        <section className="rounded-md border border-border p-4 text-sm text-ink whitespace-pre-wrap">
          {narrative}
        </section>
      ) : null}
      <EvidenceBlock title="S10 — Release summary" value={evidence.s10_release_summary} />
      <div className="grid gap-4 lg:grid-cols-2">
        <EvidenceBlock title="S8 — Security findings" value={evidence.s8_boundary_scan} />
        <EvidenceBlock title="S9 — Report metrics" value={evidence.s9_report} />
        <EvidenceBlock title="S7 — Classifications" value={evidence.s7_classification} />
      </div>
    </div>
  );
}
