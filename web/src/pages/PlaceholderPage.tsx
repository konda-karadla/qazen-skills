import { PageHeader, EmptyState } from "../components/ui/EmptyState";

export function PlaceholderPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div>
      <PageHeader title={title} description={description} />
      <EmptyState title="Coming in a later phase" description={description} />
    </div>
  );
}
