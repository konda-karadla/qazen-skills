import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/ui/EmptyState";
import { ErrorBanner, LoadingSkeleton } from "../components/ui/AsyncState";
import { Card } from "../components/ui/Card";
import { api } from "../api/client";
import type { SkillDetail, SkillListItem } from "../api/types";

export function SkillsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selected = (searchParams.get("id") || "S1").toUpperCase();
  const [skills, setSkills] = useState<SkillListItem[]>([]);
  const [detail, setDetail] = useState<SkillDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const list = await api.listSkills();
        if (cancelled) return;
        setSkills(list.skills);
        const id =
          list.skills.find((s) => s.id === selected)?.id || list.skills[0]?.id || "S1";
        if (id !== selected) {
          setSearchParams({ id }, { replace: true });
          return;
        }
        const body = await api.getSkill(id);
        if (!cancelled) setDetail(body);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load skills");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selected, setSearchParams]);

  return (
    <div>
      <PageHeader
        title="Skill definitions"
        description="Read-only view of skills/*/skill.md used by the LLM Gateway. Editing is not wired."
      />
      {error ? <ErrorBanner message={error} /> : null}
      {loading && !detail ? <LoadingSkeleton rows={4} label="Loading skills…" /> : null}

      <div className="mt-4 grid gap-4 lg:grid-cols-[200px_minmax(0,1fr)]">
        <Card title="Skills">
          <ul className="space-y-1 text-sm">
            {skills.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  className={`w-full rounded-md px-2 py-1.5 text-left font-mono text-xs ${
                    s.id === selected
                      ? "bg-primary-soft text-primary"
                      : "text-ink hover:bg-canvas"
                  }`}
                  onClick={() => setSearchParams({ id: s.id })}
                >
                  {s.id}
                </button>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-muted">
            Also see <Link className="text-primary hover:underline" to="/settings">Settings</Link>{" "}
            for the active LLM profile.
          </p>
        </Card>

        <Card title={detail ? `${detail.id} — ${detail.path}` : "Skill markdown"}>
          {detail ? (
            <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap rounded-md bg-canvas p-3 font-mono text-xs leading-relaxed text-ink">
              {detail.markdown}
            </pre>
          ) : (
            <p className="text-sm text-muted">Select a skill.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
