"use client";

import Link from "next/link";
import { useState } from "react";

import { useActiveBike } from "@/components/ActiveBikeProvider";
import { readApiError } from "@/lib/api-errors";
import type { Bike } from "@/lib/bikes";

function bikeTypeLabel(bike: Bike): string {
  return bike.bike_type === "dirt_bike" ? "Dirt bike" : "Motorcycle";
}

function hoursLabel(bike: Bike): string {
  if (bike.current_engine_hours === null) {
    return "Hours not set";
  }
  const qualifier = bike.current_engine_hours_is_estimated ? " est." : "";
  return `${bike.current_engine_hours.toFixed(1)} hrs${qualifier}`;
}

function BikeCard({
  bike,
  active,
  busy,
  onSelect,
  onRestore,
}: {
  bike: Bike;
  active: boolean;
  busy: boolean;
  onSelect: () => void;
  onRestore: () => void;
}) {
  const archived = bike.status === "archive";

  return (
    <article className={`glass-card bike-card${active ? " bike-card-active" : ""}`}>
      <div className="bike-card-heading">
        <div>
          <span className={`bike-status bike-status-${bike.status}`}>
            {active ? "Active machine" : bike.status}
          </span>
          <h3>
            <Link href={`/garage/${bike.id}`}>{bike.nickname}</Link>
          </h3>
          <p>
            {bike.year} {bike.make} {bike.model}
          </p>
        </div>
        <strong>{bike.displacement} cc</strong>
      </div>
      <dl className="bike-card-facts">
        <div>
          <dt>Configuration</dt>
          <dd>
            {bike.stroke_type} · {bikeTypeLabel(bike)}
          </dd>
        </div>
        <div>
          <dt>Engine time</dt>
          <dd>{hoursLabel(bike)}</dd>
        </div>
      </dl>
      <div className="bike-card-actions">
        <Link className="garage-action garage-action-secondary" href={`/garage/${bike.id}`}>
          View machine
        </Link>
        {archived ? (
          <button
            className="garage-action garage-action-primary"
            type="button"
            disabled={busy}
            onClick={onRestore}
          >
            {busy ? "Restoring…" : "Restore"}
          </button>
        ) : (
          <button
            className="garage-action garage-action-primary"
            type="button"
            disabled={active || busy}
            onClick={onSelect}
          >
            {active ? "Selected" : busy ? "Selecting…" : "Set active"}
          </button>
        )}
      </div>
    </article>
  );
}

export function GarageList() {
  const { bikes, activeBike, state, isSaving, error, selectBike, reload } = useActiveBike();
  const [restoringBikeId, setRestoringBikeId] = useState<string | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  async function restoreBike(bikeId: string) {
    setRestoringBikeId(bikeId);
    setRestoreError(null);
    try {
      const response = await fetch(`/api/bikes/${encodeURIComponent(bikeId)}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ status: "active" }),
      });
      if (!response.ok) {
        throw new Error(await readApiError(response, "Could not restore this bike"));
      }
      await reload();
    } catch (caught) {
      setRestoreError(caught instanceof Error ? caught.message : "Could not restore this bike");
    } finally {
      setRestoringBikeId(null);
    }
  }

  if (state === "loading") {
    return (
      <article className="glass-card garage-state-card" aria-live="polite">
        <span className="garage-spinner" aria-hidden="true" />
        <div>
          <h3>Loading your machines</h3>
          <p>Syncing Garage with your Vroometr account.</p>
        </div>
      </article>
    );
  }

  if (state === "error") {
    return (
      <article className="glass-card garage-state-card" role="alert">
        <div>
          <h3>Garage is unavailable</h3>
          <p>{error}</p>
        </div>
        <button
          className="garage-action garage-action-primary"
          type="button"
          onClick={() => void reload()}
        >
          Try again
        </button>
      </article>
    );
  }

  const availableBikes = bikes.filter((bike) => bike.status !== "archive");
  const archivedBikes = bikes.filter((bike) => bike.status === "archive");
  const mutationError = restoreError ?? error;

  return (
    <div className="garage-stack">
      <div className="garage-toolbar">
        <p>
          {availableBikes.length} available · {archivedBikes.length} archived
        </p>
        <Link className="garage-action garage-action-primary" href="/garage/new">
          + Add bike
        </Link>
      </div>

      {mutationError ? (
        <div className="garage-inline-error" role="alert">
          {mutationError}
        </div>
      ) : null}

      {bikes.length === 0 ? (
        <article className="glass-card garage-empty">
          <span aria-hidden="true">▣</span>
          <h3>Bring your first machine into Garage</h3>
          <p>
            Add the facts Vroometr will use for maintenance, rides, documents, and
            bike-specific assistance.
          </p>
          <Link className="garage-action garage-action-primary" href="/garage/new">
            Add your first bike
          </Link>
        </article>
      ) : (
        <>
          <section className="garage-section" aria-labelledby="available-bikes">
            <div className="garage-section-heading">
              <div>
                <small>AVAILABLE</small>
                <h3 id="available-bikes">Your machines</h3>
              </div>
              <span>{availableBikes.length}</span>
            </div>
            {availableBikes.length === 0 ? (
              <article className="glass-card garage-section-empty">
                <p>No available bikes. Restore one below or add another machine.</p>
              </article>
            ) : (
              <div className="bike-card-grid">
                {availableBikes.map((bike) => (
                  <BikeCard
                    key={bike.id}
                    bike={bike}
                    active={activeBike?.id === bike.id}
                    busy={isSaving}
                    onSelect={() => void selectBike(bike.id)}
                    onRestore={() => undefined}
                  />
                ))}
              </div>
            )}
          </section>

          {archivedBikes.length > 0 ? (
            <section className="garage-section garage-archive" aria-labelledby="archived-bikes">
              <div className="garage-section-heading">
                <div>
                  <small>HISTORY</small>
                  <h3 id="archived-bikes">Archived</h3>
                </div>
                <span>{archivedBikes.length}</span>
              </div>
              <div className="bike-card-grid">
                {archivedBikes.map((bike) => (
                  <BikeCard
                    key={bike.id}
                    bike={bike}
                    active={false}
                    busy={restoringBikeId === bike.id}
                    onSelect={() => undefined}
                    onRestore={() => void restoreBike(bike.id)}
                  />
                ))}
              </div>
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}
