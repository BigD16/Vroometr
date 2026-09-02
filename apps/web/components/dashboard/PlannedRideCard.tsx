import { mockPlannedRide } from "@/lib/mock-machine";

export function PlannedRideCard() {
  return (
    <article className="glass-card next-ride">
      <time>
        <b>{mockPlannedRide.day}</b>
        <span>{mockPlannedRide.month}</span>
      </time>
      <div>
        <small>PLANNED RIDE</small>
        <h3>{mockPlannedRide.name}</h3>
        <p>{mockPlannedRide.detail}</p>
      </div>
      <button type="button" aria-label="Open planned ride">
        →
      </button>
    </article>
  );
}
