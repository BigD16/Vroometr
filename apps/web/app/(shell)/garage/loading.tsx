import { WorkspacePage } from "@/components/WorkspacePage";

export default function GarageLoading() {
  return (
    <WorkspacePage
      kicker="YOUR MACHINES"
      title="Garage"
      description="Loading your machine profile."
      wide
    >
      <article className="glass-card garage-state-card" aria-live="polite">
        <span className="garage-spinner" aria-hidden="true" />
        <div>
          <h3>Loading machine</h3>
          <p>Reading the latest owner-scoped details from Vroometr.</p>
        </div>
      </article>
    </WorkspacePage>
  );
}
