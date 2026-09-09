import type { Bike } from "@/lib/bikes";

function powertrainLabel(bike: Bike | null): string {
  if (bike === null) {
    return "—";
  }
  if (bike.powertrain_type === "electric") {
    return "ELECTRIC";
  }
  return bike.stroke_type ?? "COMBUSTION";
}

export function MetricsStrip({ bike }: { bike: Bike | null }) {
  const currentHours = bike?.current_engine_hours ?? null;
  const hasHours = currentHours !== null;

  return (
    <section className="metrics">
      <div>
        <small>ENGINE HOURS</small>
        <b>
          {hasHours ? currentHours.toFixed(1) : "—"}{" "}
          <em>
            {hasHours
              ? bike?.current_engine_hours_is_estimated
                ? "EST. HRS"
                : "HRS"
              : "NOT SET"}
          </em>
        </b>
      </div>
      <div>
        <small>MAINTENANCE</small>
        <b>
          — <em>NO HISTORY</em>
        </b>
      </div>
      <div>
        <small>POWERTRAIN</small>
        <b>{powertrainLabel(bike)}</b>
      </div>
      <div>
        <small>LAST RIDE</small>
        <b>
          — <em>NO HISTORY</em>
        </b>
      </div>
    </section>
  );
}
