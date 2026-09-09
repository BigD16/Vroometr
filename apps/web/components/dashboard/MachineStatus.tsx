import type { Bike } from "@/lib/bikes";

function powertrainLabel(bike: Bike): string {
  if (bike.powertrain_type === "electric") {
    return "Electric";
  }
  if (bike.stroke_type === "2T") {
    return "Two-stroke";
  }
  if (bike.stroke_type === "4T") {
    return "Four-stroke";
  }
  return "Combustion";
}

export function MachineStatus({ bike }: { bike: Bike | null }) {
  if (bike === null) {
    return (
      <section className="scene-label">
        <small>MACHINE STATUS</small>
        <h2>NO ACTIVE MACHINE</h2>
        <p>Add a bike in Garage to begin building its history.</p>
      </section>
    );
  }

  return (
    <section className="scene-label">
      <small>ACTIVE MACHINE</small>
      <h2>
        {bike.nickname} <i aria-hidden="true" />
      </h2>
      <p>
        {bike.year} {bike.make} {bike.model} · {powertrainLabel(bike)}
      </p>
    </section>
  );
}
