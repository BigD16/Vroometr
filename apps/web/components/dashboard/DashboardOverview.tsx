"use client";

import { useActiveBike } from "@/components/ActiveBikeProvider";
import { MachineHealthCard } from "@/components/dashboard/MachineHealthCard";
import { MachineStatus } from "@/components/dashboard/MachineStatus";
import { MetricsStrip } from "@/components/dashboard/MetricsStrip";
import { PlannedRideCard } from "@/components/dashboard/PlannedRideCard";
import { UpNextCard } from "@/components/dashboard/UpNextCard";

export function DashboardOverview() {
  const { activeBike, state, error, reload } = useActiveBike();

  if (state !== "ready") {
    const failed = state === "error";
    return (
      <>
        <section className="scene-label">
          <small>MACHINE CONTEXT</small>
          <h2>{failed ? "GARAGE UNAVAILABLE" : "SYNCING GARAGE"}</h2>
          <p>{failed ? "Vroometr could not load your active machine." : "Loading your machine…"}</p>
        </section>
        <aside className="panel-stack right-panel">
          <article
            className="glass-card dashboard-context-state"
            role={failed ? "alert" : "status"}
          >
            <span
              className={failed ? "dashboard-state-mark dashboard-state-error" : "garage-spinner"}
              aria-hidden="true"
            />
            <div>
              <strong>{failed ? "Machine context unavailable" : "Syncing machine context"}</strong>
              <p>{failed ? error : "Your dashboard will be ready in a moment."}</p>
            </div>
            {failed ? (
              <button type="button" onClick={() => void reload()}>
                Try again
              </button>
            ) : null}
          </article>
        </aside>
        <MetricsStrip bike={null} />
      </>
    );
  }

  return (
    <>
      <MachineStatus bike={activeBike} />
      <aside className="panel-stack right-panel">
        <MachineHealthCard bike={activeBike} />
        <UpNextCard bike={activeBike} />
        <PlannedRideCard bike={activeBike} />
      </aside>
      <MetricsStrip bike={activeBike} />
    </>
  );
}
