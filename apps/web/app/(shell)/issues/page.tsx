import { WorkspacePage } from "@/components/WorkspacePage";

export default function IssuesPage() {
  return (
    <WorkspacePage
      kicker="TROUBLESHOOTING"
      title="Issues"
      description="What went wrong, what you tried, and how it resolved."
    >
      <article className="glass-card">
        <p>No issues on the dashboard. This list is a placeholder until Phase 7.</p>
      </article>
    </WorkspacePage>
  );
}
