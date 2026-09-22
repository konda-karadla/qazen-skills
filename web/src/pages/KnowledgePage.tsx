import { useEffect, useState } from "react";
import { PageHeader, EmptyState } from "../components/ui/EmptyState";
import { ErrorBanner, LoadingSkeleton } from "../components/ui/AsyncState";
import { StatusPill } from "../components/ui/StatusPill";
import { Table, THead, Th, Td } from "../components/ui/Table";
import { api, formatWhen } from "../api/client";
import type { KnowledgeItem } from "../api/types";

export function KnowledgePage() {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [message, setMessage] = useState<string>("");
  const [writable, setWritable] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getKnowledge(100);
        if (cancelled) return;
        setItems(data.items);
        setMessage(data.message);
        setWritable(Boolean(data.writable));
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load knowledge");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  return (
    <div>
      <PageHeader
        title="Knowledge Base"
        description="Human-confirmed domain rules. Read-only in v1 — application writes are not wired."
        actions={<StatusPill tone="muted">{writable ? "Writable" : "Read-only"}</StatusPill>}
      />

      {error ? <ErrorBanner message={error} onRetry={() => setReloadKey((k) => k + 1)} /> : null}
      {loading ? <LoadingSkeleton rows={3} label="Loading knowledge…" /> : null}

      <p className="mb-4 rounded-md border border-dashed border-border bg-canvas px-3 py-2 text-xs text-muted">
        {message || "Human-confirmed rules will appear here. Application writes are not wired yet."}
        {" "}
        No Add / Edit / Delete controls are shown because writes are not available.
      </p>

      {!loading && items.length === 0 ? (
        <EmptyState
          title="No confirmed rules yet"
          description="Rules appear after humans confirm domain knowledge. Add Rule is not available in v1."
        />
      ) : items.length > 0 ? (
        <Table>
          <THead>
            <tr>
              <Th>Domain</Th>
              <Th>Rule</Th>
              <Th>Status</Th>
              <Th>Source</Th>
              <Th>Created</Th>
            </tr>
          </THead>
          <tbody className="divide-y divide-border">
            {items.map((item) => (
              <tr key={item.knowledge_id}>
                <Td className="text-sm font-medium">{item.domain}</Td>
                <Td className="max-w-xl text-sm">{item.rule}</Td>
                <Td>
                  <StatusPill tone={item.status === "confirmed" ? "success" : "muted"}>
                    {item.status}
                  </StatusPill>
                </Td>
                <Td className="text-xs text-muted">{item.source || "—"}</Td>
                <Td className="text-xs text-muted">{formatWhen(item.created_at)}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      ) : null}
    </div>
  );
}
