"use client";

import { useEffect } from "react";

import { WorkspacePage } from "@/components/WorkspacePage";

export default function GarageError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    console.error("Garage route failed", { digest: error.digest });
  }, [error]);

  return (
    <WorkspacePage
      kicker="GARAGE / ERROR"
      title="Garage hit a snag"
      description="Your machine data is still safe. This view could not be loaded."
      wide
    >
      <article className="glass-card garage-state-card" role="alert">
        <div>
          <h3>Could not load this Garage view</h3>
          <p>Check the API connection and try the request again.</p>
        </div>
        <button className="garage-action garage-action-primary" type="button" onClick={retry}>
          Try again
        </button>
      </article>
    </WorkspacePage>
  );
}
