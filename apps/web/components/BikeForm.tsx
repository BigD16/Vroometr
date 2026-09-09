"use client";

import type { FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useActiveBike } from "@/components/ActiveBikeProvider";
import { readApiError } from "@/lib/api-errors";
import type { Bike } from "@/lib/bikes";

function text(formData: FormData, name: string): string {
  return String(formData.get(name) ?? "").trim();
}

function nullableNumber(formData: FormData, name: string): number | null {
  const value = text(formData, name);
  return value === "" ? null : Number(value);
}

export function BikeForm({ bike }: { bike?: Bike }) {
  const editing = bike !== undefined;
  const router = useRouter();
  const { reload, selectBike } = useActiveBike();
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setError(null);

    const formData = new FormData(event.currentTarget);
    const payload = {
      nickname: text(formData, "nickname"),
      make: text(formData, "make"),
      model: text(formData, "model"),
      year: Number(text(formData, "year")),
      displacement: Number(text(formData, "displacement")),
      bike_type: text(formData, "bike_type"),
      stroke_type: text(formData, "stroke_type"),
      purchase_date: text(formData, "purchase_date") || null,
      engine_hours_at_purchase: nullableNumber(formData, "engine_hours_at_purchase"),
      current_engine_hours: nullableNumber(formData, "current_engine_hours"),
      current_engine_hours_is_estimated:
        formData.get("current_engine_hours_is_estimated") === "on",
      status: editing ? text(formData, "status") : "active",
      unit_preference: text(formData, "unit_preference"),
    };

    try {
      const response = await fetch(
        editing ? `/api/bikes/${encodeURIComponent(bike.id)}` : "/api/bikes",
        {
          method: editing ? "PATCH" : "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      if (!response.ok) {
        throw new Error(
          await readApiError(response, editing ? "Could not update this bike" : "Could not add bike"),
        );
      }

      const savedBike = (await response.json()) as Bike;
      await reload();
      if (!editing) {
        await selectBike(savedBike.id);
      }
      router.push(`/garage/${savedBike.id}`);
      router.refresh();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : editing
            ? "Could not update this bike"
            : "Could not add bike",
      );
      setIsSaving(false);
    }
  }

  return (
    <form className="glass-card bike-form" onSubmit={submit}>
      <div className="bike-form-intro">
        <div>
          <small>{editing ? "MACHINE PROFILE" : "NEW MACHINE"}</small>
          <h3>{editing ? `Update ${bike.nickname}` : "Tell Vroometr what you ride"}</h3>
        </div>
        <p>These structured facts become the trusted identity for this machine.</p>
      </div>

      {error ? (
        <div className="garage-inline-error" role="alert">
          {error}
        </div>
      ) : null}

      <fieldset disabled={isSaving}>
        <section className="bike-form-section" aria-labelledby="identity-heading">
          <div className="bike-form-section-title">
            <span>01</span>
            <div>
              <h4 id="identity-heading">Identity</h4>
              <p>The name and core configuration you use for this bike.</p>
            </div>
          </div>
          <div className="bike-form-grid">
            <label className="bike-field bike-field-wide">
              <span>Nickname</span>
              <input
                name="nickname"
                defaultValue={bike?.nickname}
                placeholder="Trail bike"
                maxLength={255}
                required
              />
            </label>
            <label className="bike-field">
              <span>Make</span>
              <input
                name="make"
                defaultValue={bike?.make}
                placeholder="Yamaha"
                maxLength={255}
                required
              />
            </label>
            <label className="bike-field">
              <span>Model</span>
              <input
                name="model"
                defaultValue={bike?.model}
                placeholder="YZ250"
                maxLength={255}
                required
              />
            </label>
            <label className="bike-field">
              <span>Year</span>
              <input
                name="year"
                type="number"
                defaultValue={bike?.year}
                min={1900}
                inputMode="numeric"
                placeholder="2024"
                required
              />
            </label>
            <label className="bike-field">
              <span>Displacement</span>
              <span className="bike-input-with-unit">
                <input
                  name="displacement"
                  type="number"
                  defaultValue={bike?.displacement}
                  min={1}
                  inputMode="numeric"
                  placeholder="250"
                  required
                />
                <em>cc</em>
              </span>
            </label>
            <label className="bike-field">
              <span>Machine type</span>
              <select name="bike_type" defaultValue={bike?.bike_type ?? "dirt_bike"} required>
                <option value="dirt_bike">Dirt bike</option>
                <option value="motorcycle">Motorcycle</option>
              </select>
            </label>
            <label className="bike-field">
              <span>Engine cycle</span>
              <select name="stroke_type" defaultValue={bike?.stroke_type ?? "4T"} required>
                <option value="2T">Two-stroke (2T)</option>
                <option value="4T">Four-stroke (4T)</option>
              </select>
            </label>
          </div>
        </section>

        <section className="bike-form-section" aria-labelledby="history-heading">
          <div className="bike-form-section-title">
            <span>02</span>
            <div>
              <h4 id="history-heading">Ownership & engine time</h4>
              <p>Optional baseline information. You can add or correct it later.</p>
            </div>
          </div>
          <div className="bike-form-grid">
            <label className="bike-field">
              <span>Purchase date</span>
              <input name="purchase_date" type="date" defaultValue={bike?.purchase_date ?? ""} />
            </label>
            <label className="bike-field">
              <span>Hours at purchase</span>
              <input
                name="engine_hours_at_purchase"
                type="number"
                defaultValue={bike?.engine_hours_at_purchase ?? ""}
                min={0}
                step="0.1"
                inputMode="decimal"
                placeholder="Optional"
              />
            </label>
            <label className="bike-field">
              <span>Current engine hours</span>
              <input
                name="current_engine_hours"
                type="number"
                defaultValue={bike?.current_engine_hours ?? ""}
                min={0}
                step="0.1"
                inputMode="decimal"
                placeholder="Optional"
              />
            </label>
            <label className="bike-check-field">
              <input
                name="current_engine_hours_is_estimated"
                type="checkbox"
                defaultChecked={bike?.current_engine_hours_is_estimated ?? true}
              />
              <span>
                <strong>Estimated reading</strong>
                <small>Turn off when this came from a confirmed meter reading.</small>
              </span>
            </label>
          </div>
        </section>

        <section className="bike-form-section" aria-labelledby="preferences-heading">
          <div className="bike-form-section-title">
            <span>03</span>
            <div>
              <h4 id="preferences-heading">Preferences</h4>
              <p>Controls how this machine appears in Garage.</p>
            </div>
          </div>
          <div className="bike-form-grid">
            <label className="bike-field">
              <span>Units</span>
              <select
                name="unit_preference"
                defaultValue={bike?.unit_preference ?? "imperial"}
                required
              >
                <option value="imperial">Imperial</option>
                <option value="metric">Metric</option>
              </select>
            </label>
            {editing ? (
              <label className="bike-field">
                <span>Garage status</span>
                <select name="status" defaultValue={bike.status} required>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="archive">Archived</option>
                </select>
                <small>Archived bikes leave active context but remain in your history.</small>
              </label>
            ) : (
              <div className="bike-form-default">
                <span>Initial status</span>
                <strong>Active</strong>
                <small>The new bike will become your active machine.</small>
              </div>
            )}
          </div>
        </section>
      </fieldset>

      <div className="bike-form-actions">
        <Link
          className="garage-action garage-action-secondary"
          href={editing ? `/garage/${bike.id}` : "/garage"}
        >
          Cancel
        </Link>
        <button className="garage-action garage-action-primary" type="submit" disabled={isSaving}>
          {isSaving ? "Saving…" : editing ? "Save changes" : "Add bike"}
        </button>
      </div>
    </form>
  );
}
