import Link from "next/link";

import type { Bike } from "@/lib/bikes";

export function UpNextCard({ bike }: { bike: Bike | null }) {
  return (
    <article className="glass-card">
      <header>
        <span>UP NEXT</span>
        <Link className="dashboard-card-link" href="/maintenance">
          VIEW ALL →
        </Link>
      </header>
      <div className="dashboard-card-empty">
        <span aria-hidden="true">◇</span>
        <div>
          <b>{bike === null ? "No active machine" : "No verified tasks yet"}</b>
          <p>
            {bike === null
              ? "Add a bike before building a maintenance plan."
              : "Maintenance recommendations will appear after a verified service plan is available."}
          </p>
        </div>
      </div>
    </article>
  );
}
