(() => {
  const $ = (id) => document.getElementById(id);

  const state = { runId: null };

  function qsRunId() {
    return new URLSearchParams(location.search).get("run_id") || "";
  }

  function setFeedback(el, text, kind) {
    el.textContent = text || "";
    el.classList.remove("error", "ok");
    if (kind) el.classList.add(kind);
  }

  async function api(path, options) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
      ...options,
    });
    const text = await res.text();
    let data;
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { detail: text };
    }
    if (!res.ok) {
      const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data);
      throw new Error(detail || `HTTP ${res.status}`);
    }
    return data;
  }

  function highlightForGate(gate, evidence) {
    const panel = $("highlight-panel");
    const title = $("highlight-title");
    const body = $("highlight-body");
    if (!gate || !evidence) {
      panel.hidden = true;
      return;
    }
    if (gate === "H4" && evidence.s9_report) {
      title.textContent = "H4 — Execution summary";
      body.textContent = evidence.s9_report.human_readable_summary || JSON.stringify(evidence.s9_report.aggregate_metrics, null, 2);
      panel.hidden = false;
      return;
    }
    if (gate === "H5" && evidence.s10_release_summary) {
      const s10 = evidence.s10_release_summary;
      title.textContent = "H5 — Factual release summary";
      body.textContent = s10.factual_narrative
        || [
          `Pass/fail: ${JSON.stringify(s10.pass_fail_summary || {})}`,
          `App bugs: ${(s10.outstanding_app_bugs || []).length}`,
          `Security violations: ${(s10.security_violations || []).length}`,
          s10.data_completeness_note || "",
        ].filter(Boolean).join("\n");
      panel.hidden = false;
      return;
    }
    panel.hidden = true;
  }

  function renderEvidence(evidence) {
    const list = $("evidence-list");
    list.innerHTML = "";
    const keys = Object.keys(evidence || {});
    if (!keys.length) {
      list.innerHTML = "<p class='message'>No evidence artifacts for this gate.</p>";
      return;
    }
    const preferredOpen = new Set(["s9_report", "s10_release_summary", "s2_ambiguity_analysis"]);
    for (const key of keys) {
      const details = document.createElement("details");
      details.className = "artifact";
      details.open = preferredOpen.has(key) || keys.length <= 2;
      const summary = document.createElement("summary");
      summary.textContent = key;
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(evidence[key], null, 2);
      details.append(summary, pre);
      list.append(details);
    }
  }

  async function loadRuns() {
    const list = $("runs-list");
    try {
      const data = await api("/runs?limit=15");
      const runs = data.runs || [];
      if (!runs.length) {
        list.innerHTML = "<p class='message'>No runs yet. Paste a requirement above and click Start run.</p>";
        return;
      }
      list.innerHTML = "";
      for (const run of runs) {
        const row = document.createElement("div");
        row.className = "run-row";
        row.innerHTML = `
          <span class="id">${run.run_id}</span>
          <span class="meta">${run.status || "—"} · ${run.current_stage || "—"}</span>
          <span class="gate-pill">${run.pending_gate || "—"}</span>
        `;
        row.addEventListener("click", () => {
          $("run-id").value = run.run_id;
          loadReview(run.run_id).catch((err) => {
            $("status-panel").hidden = false;
            $("status-message").textContent = err.message || String(err);
          });
        });
        list.append(row);
      }
    } catch (err) {
      list.innerHTML = `<p class="message error">${err.message || String(err)}</p>`;
    }
  }

  async function loadReview(runId) {
    state.runId = runId;
    const data = await api(`/runs/${encodeURIComponent(runId)}/review`);
    $("status-panel").hidden = false;
    $("pending-gate").textContent = data.pending_gate || "none";
    $("run-status").textContent = data.run_status || "—";
    $("current-stage").textContent = data.current_stage || "—";
    $("status-message").textContent = data.message || (
      data.pending_gate
        ? `Review ${data.pending_gate} using the evidence below, then approve, request changes, or reject.`
        : "No pending gate."
    );

    const hasPending = Boolean(data.pending_gate);
    $("actions").hidden = !hasPending;
    $("evidence-panel").hidden = !hasPending;
    $("history-panel").hidden = true;
    if (hasPending) {
      renderEvidence(data.evidence || {});
      highlightForGate(data.pending_gate, data.evidence || {});
    } else {
      $("highlight-panel").hidden = true;
    }
    setFeedback($("action-feedback"), "", null);

    const url = new URL(location.href);
    url.searchParams.set("run_id", runId);
    history.replaceState({}, "", url);
    loadRuns();
  }

  async function decide(kind) {
    if (!state.runId) return;
    const reviewer = $("reviewer").value.trim();
    if (!reviewer) {
      setFeedback($("action-feedback"), "Reviewer is required.", "error");
      return;
    }
    const body = JSON.stringify({
      reviewer,
      comment: $("comment").value.trim() || null,
    });
    try {
      const busy =
        kind === "request-changes"
          ? "Revising prior stage (may take several minutes with a local LLM)…"
          : `${kind} in progress…`;
      setFeedback($("action-feedback"), busy, null);
      await api(`/runs/${encodeURIComponent(state.runId)}/${kind}`, {
        method: "POST",
        body,
      });
      const ok =
        kind === "request-changes"
          ? "Revision finished. Same gate is pending again with updated evidence."
          : `${kind} succeeded.`;
      setFeedback($("action-feedback"), ok, "ok");
      await loadReview(state.runId);
    } catch (err) {
      setFeedback($("action-feedback"), err.message || String(err), "error");
    }
  }

  async function loadHistory() {
    if (!state.runId) return;
    const data = await api(`/runs/${encodeURIComponent(state.runId)}/history`);
    const panel = $("history-panel");
    const list = $("history-list");
    list.innerHTML = "";
    const rows = data.history || [];
    if (!rows.length) {
      list.innerHTML = "<p class='message'>No decisions recorded yet.</p>";
    } else {
      for (const row of rows) {
        const div = document.createElement("div");
        div.className = "history-row";
        div.innerHTML = `
          <span class="gate">${row.gate || ""}</span>
          <span class="decision">${row.decision || ""}</span>
          <span>${row.reviewer || "—"} ${row.comment ? "· " + row.comment : ""}</span>
        `;
        list.append(div);
      }
    }
    panel.hidden = false;
  }

  $("load-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const runId = $("run-id").value.trim();
    if (!runId) return;
    try {
      await loadReview(runId);
    } catch (err) {
      $("status-panel").hidden = false;
      $("pending-gate").textContent = "—";
      $("run-status").textContent = "error";
      $("current-stage").textContent = "—";
      $("status-message").textContent = err.message || String(err);
      $("actions").hidden = true;
      $("evidence-panel").hidden = true;
      $("highlight-panel").hidden = true;
    }
  });

  $("start-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const raw = $("requirement-text").value.trim();
    if (!raw) {
      setFeedback($("start-feedback"), "Requirement text is required.", "error");
      return;
    }
    const requirementId = $("requirement-id").value.trim();
    const body = { input: { raw } };
    if (requirementId) body.requirement_id = requirementId;

    const btn = $("btn-start-run");
    btn.disabled = true;
    try {
      setFeedback(
        $("start-feedback"),
        "Starting run (S1–S2 may take a few minutes with a local LLM)…",
        null,
      );
      const data = await api("/runs", { method: "POST", body: JSON.stringify(body) });
      const runId = data.run_id;
      if (!runId) throw new Error("Orchestrator did not return run_id");
      $("run-id").value = runId;
      setFeedback($("start-feedback"), `Run started: ${runId}`, "ok");
      await loadReview(runId);
    } catch (err) {
      setFeedback($("start-feedback"), err.message || String(err), "error");
    } finally {
      btn.disabled = false;
    }
  });

  $("btn-approve").addEventListener("click", () => decide("approve"));
  $("btn-reject").addEventListener("click", () => decide("reject"));
  $("btn-changes").addEventListener("click", () => decide("request-changes"));
  $("btn-history").addEventListener("click", () => {
    loadHistory().catch((err) => setFeedback($("action-feedback"), err.message, "error"));
  });
  $("btn-refresh-runs").addEventListener("click", () => loadRuns());

  loadRuns();

  const initial = qsRunId();
  if (initial) {
    $("run-id").value = initial;
    loadReview(initial).catch((err) => {
      $("status-panel").hidden = false;
      $("status-message").textContent = err.message || String(err);
    });
  }
})();
