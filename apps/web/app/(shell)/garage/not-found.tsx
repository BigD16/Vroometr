import Link from "next/link";

import { WorkspacePage } from "@/components/WorkspacePage";

export default function BikeNotFound() {
  return (
    <WorkspacePage
      kicker="GARAGE / NOT FOUND"
      title="Bike not found"
      description="This machine does not exist or does not belong to your account."
      wide
    >
      <article className="glass-card garage-state-card">
        <div>
          <h3>That machine is not in your Garage</h3>
          <p>Ownership stays enforced by FastAPI, even when a bike URL is entered directly.</p>
        </div>
        <Link className="garage-action garage-action-primary" href="/garage">
          Back to Garage
        </Link>
      </article>
    </WorkspacePage>
  );
}
