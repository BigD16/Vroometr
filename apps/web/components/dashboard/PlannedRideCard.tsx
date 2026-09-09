import Link from "next/link";

import type { Bike } from "@/lib/bikes";

export function PlannedRideCard({ bike }: { bike: Bike | null }) {
  return (
    <article className="glass-card next-ride">
      <time>
        <b>—</b>
        <span>RIDE</span>
      </time>
      <div>
        <small>PLANNED RIDE</small>
        <h3>{bike === null ? "No active machine" : "Nothing scheduled"}</h3>
        <p>
          {bike === null
            ? "Add a bike before planning a ride."
            : "Upcoming rides will appear here when ride tracking is available."}
        </p>
      </div>
      <Link href="/rides" aria-label="Open rides">
        →
      </Link>
    </article>
  );
}
