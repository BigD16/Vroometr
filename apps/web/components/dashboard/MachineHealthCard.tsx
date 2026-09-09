import type { Bike } from "@/lib/bikes";

export function MachineHealthCard({ bike }: { bike: Bike | null }) {
  const hasBike = bike !== null;

  return (
    <article className="glass-card health">
      <header>
        <span>MACHINE HEALTH</span>
        <b>—</b>
      </header>
      <div className="meter meter-empty" aria-hidden="true" />
      <footer>
        <strong>{hasBike ? "NOT CALCULATED" : "NO MACHINE"}</strong>
        <span>
          {hasBike
            ? "Health appears when verified maintenance data is available."
            : "Add a bike to begin tracking machine health."}
        </span>
      </footer>
    </article>
  );
}
