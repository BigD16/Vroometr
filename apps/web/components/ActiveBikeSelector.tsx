"use client";

import { useActiveBike } from "@/components/ActiveBikeProvider";
import type { BikeSummary } from "@/lib/bikes";

function identityLine(bike: BikeSummary): string {
  let powertrain = "Combustion";
  if (bike.powertrain_type === "electric") {
    powertrain = "Electric";
  } else if (bike.stroke_type === "2T") {
    powertrain = "Two-stroke";
  } else if (bike.stroke_type === "4T") {
    powertrain = "Four-stroke";
  }
  return `${bike.year} ${bike.make} ${bike.model} · ${powertrain}`;
}

export function ActiveBikeSelector() {
  const { bikes, activeBike, state, isSaving, error, selectBike, reload } = useActiveBike();
  const selectableBikes = bikes.filter((bike) => bike.status !== "archive");

  if (state === "loading") {
    return (
      <div className="machine-title" aria-live="polite">
        <span>
          <i /> ACTIVE MACHINE
        </span>
        <strong className="active-bike-status">Loading bikes…</strong>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="machine-title" role="alert">
        <span>BIKE CONTEXT UNAVAILABLE</span>
        <button className="active-bike-retry" type="button" onClick={() => void reload()}>
          Try again
        </button>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="machine-title">
      <label htmlFor="active-bike">
        <i /> ACTIVE MACHINE
      </label>
      <select
        id="active-bike"
        value={activeBike?.id ?? ""}
        disabled={isSaving || selectableBikes.length === 0}
        onChange={(event) => void selectBike(event.target.value)}
      >
        {selectableBikes.length === 0 ? <option value="">No bikes yet</option> : null}
        {activeBike === null && selectableBikes.length > 0 ? (
          <option value="">Choose a machine</option>
        ) : null}
        {selectableBikes.map((bike) => (
          <option key={bike.id} value={bike.id}>
            {bike.nickname} — {bike.year} {bike.make} {bike.model}
          </option>
        ))}
      </select>
      <p>{activeBike === null ? "Add a bike in Garage to begin." : identityLine(activeBike)}</p>
      {error ? (
        <small className="active-bike-error" role="alert">
          {error}
        </small>
      ) : null}
    </div>
  );
}
