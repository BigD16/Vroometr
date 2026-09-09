"use client";

import Link from "next/link";

import { useActiveBike } from "@/components/ActiveBikeProvider";
import type { Bike } from "@/lib/bikes";

function displayDate(value: string | null): string {
  if (value === null) {
    return "Not recorded";
  }
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function displayHours(value: number | null): string {
  return value === null ? "Not recorded" : `${value.toFixed(1)} hours`;
}

export function BikeDetails({ bike }: { bike: Bike }) {
  const { activeBike, isSaving, error, selectBike } = useActiveBike();
  const isActive = activeBike?.id === bike.id;
  const isArchived = bike.status === "archive";

  return (
    <div className="garage-detail">
      <div className="garage-detail-toolbar">
        <Link className="garage-back-link" href="/garage">
          ← All bikes
        </Link>
        <div>
          {!isArchived ? (
            <button
              className="garage-action garage-action-secondary"
              type="button"
              disabled={isActive || isSaving}
              onClick={() => void selectBike(bike.id)}
            >
              {isActive ? "Active machine" : isSaving ? "Selecting…" : "Set active"}
            </button>
          ) : null}
          <Link
            className="garage-action garage-action-primary"
            href={`/garage/${bike.id}/edit`}
          >
            Edit machine
          </Link>
        </div>
      </div>

      {error ? (
        <div className="garage-inline-error" role="alert">
          {error}
        </div>
      ) : null}

      <article className="glass-card garage-machine-hero">
        <div>
          <span className={`bike-status bike-status-${bike.status}`}>
            {isActive ? "Active machine" : bike.status}
          </span>
          <h3>{bike.nickname}</h3>
          <p>
            {bike.year} {bike.make} {bike.model}
          </p>
        </div>
        <div className="garage-machine-number">
          <strong>{bike.displacement}</strong>
          <span>CC · {bike.stroke_type}</span>
        </div>
      </article>

      <div className="garage-detail-grid">
        <article className="glass-card garage-fact-panel">
          <header>
            <span>MACHINE</span>
          </header>
          <dl>
            <div>
              <dt>Type</dt>
              <dd>{bike.bike_type === "dirt_bike" ? "Dirt bike" : "Motorcycle"}</dd>
            </div>
            <div>
              <dt>Engine</dt>
              <dd>{bike.stroke_type === "2T" ? "Two-stroke" : "Four-stroke"}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{bike.status === "archive" ? "Archived" : bike.status}</dd>
            </div>
            <div>
              <dt>Units</dt>
              <dd>{bike.unit_preference === "imperial" ? "Imperial" : "Metric"}</dd>
            </div>
          </dl>
        </article>

        <article className="glass-card garage-fact-panel">
          <header>
            <span>OWNERSHIP & HOURS</span>
          </header>
          <dl>
            <div>
              <dt>Purchased</dt>
              <dd>{displayDate(bike.purchase_date)}</dd>
            </div>
            <div>
              <dt>Hours at purchase</dt>
              <dd>{displayHours(bike.engine_hours_at_purchase)}</dd>
            </div>
            <div>
              <dt>Current hours</dt>
              <dd>{displayHours(bike.current_engine_hours)}</dd>
            </div>
            <div>
              <dt>Reading</dt>
              <dd>{bike.current_engine_hours_is_estimated ? "Estimated" : "Confirmed"}</dd>
            </div>
          </dl>
        </article>

        <article className="glass-card garage-fact-panel garage-scene-panel">
          <header>
            <span>GARAGE SCENE</span>
          </header>
          <strong>
            {bike.selected_garage_scene_id === null ? "Vroometr default" : "Personalized"}
          </strong>
          <p>
            {bike.selected_garage_scene_id === null
              ? "This bike uses the default garage backdrop."
              : "This bike has a selected personalized garage scene."}
          </p>
          <small>Personalized garage generation arrives in a later phase.</small>
        </article>
      </div>
    </div>
  );
}
