import { WorkspacePage } from "@/components/WorkspacePage";

export default function GaragePage() {
  return (
    <WorkspacePage
      kicker="YOUR MACHINES"
      title="Garage"
      description="Every bike you own, in one place."
    >
      <article className="glass-card">
        <p>Bike list is empty until Phase 2. The dashboard still uses the default garage scene.</p>
      </article>
    </WorkspacePage>
  );
}
