"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useActiveBike } from "@/components/ActiveBikeProvider";

type Option = { key: string; label: string };
type SystemOption = Option & { components: Option[] };

type Taxonomy = {
  systems: SystemOption[];
  actions: Option[];
  reasons: Option[];
  performer_types: Option[];
  evidence_types: Option[];
};

type MaintenanceRecord = {
  id: string;
  service_date: string;
  system: string;
  component: string;
  component_detail: string | null;
  action: string;
  reason: string;
  performer_type: string;
  evidence_type: string;
  engine_hours: number | null;
  details: string | null;
};

type DueItem = {
  rule_id: string;
  system: string;
  component: string;
  action: string;
  status: string;
  definitive: boolean;
  hours_remaining: number | null;
  days_remaining: number | null;
  note: string | null;
};

type ActiveBike = {
  id: string;
  nickname: string;
};

function labelFor(options: Option[], key: string) {
  return options.find((item) => item.key === key)?.label ?? key;
}

export function MaintenanceWorkspace() {
  const { activeBike, state, error, reload } = useActiveBike();
  if (state === "loading") return <p role="status">Loading your bike…</p>;
  if (state === "error") {
    return (
      <div role="alert">
        <p>{error}</p>
        <button type="button" onClick={() => void reload()}>
          Retry
        </button>
      </div>
    );
  }
  if (!activeBike) {
    return (
      <div className="glass-card maintenance-empty">
        <p>Add a bike before logging service history.</p>
        <Link href="/garage">Go to Garage</Link>
      </div>
    );
  }
  return <MaintenanceBikeWorkspace key={activeBike.id} activeBike={activeBike} />;
}

function MaintenanceBikeWorkspace({ activeBike }: { activeBike: ActiveBike }) {
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null);
  const [records, setRecords] = useState<MaintenanceRecord[]>([]);
  const [dueItems, setDueItems] = useState<DueItem[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [system, setSystem] = useState("engine");
  const [component, setComponent] = useState("engine_oil");
  const [componentDetail, setComponentDetail] = useState("");
  const [action, setAction] = useState("replace");
  const [reason, setReason] = useState("scheduled");
  const [performerType, setPerformerType] = useState("owner");
  const [evidenceType, setEvidenceType] = useState("owner_reported");
  const [serviceDate, setServiceDate] = useState(
    () => new Date().toISOString().slice(0, 10),
  );
  const [engineHours, setEngineHours] = useState("");
  const [details, setDetails] = useState("");
  const [ruleHours, setRuleHours] = useState("10");
  const refresh = useCallback(() => setRevision((value) => value + 1), []);

  const components = useMemo(() => {
    const match = taxonomy?.systems.find((item) => item.key === system);
    return match?.components ?? [];
  }, [taxonomy, system]);

  const selectedComponent = components.some((item) => item.key === component)
    ? component
    : (components[0]?.key ?? "other");

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetch("/api/maintenance/taxonomy", { signal: controller.signal }).then((response) => {
        if (!response.ok) throw new Error("Could not load taxonomy.");
        return response.json();
      }),
      fetch(`/api/maintenance?bike_id=${encodeURIComponent(activeBike.id)}`, {
        signal: controller.signal,
      }).then((response) => {
        if (!response.ok) throw new Error("Could not load maintenance data.");
        return response.json();
      }),
      fetch(
        `/api/maintenance/due-state?bike_id=${encodeURIComponent(activeBike.id)}`,
        { signal: controller.signal },
      ).then((response) => (response.ok ? response.json() : [])),
    ])
      .then(([tax, list, due]: [Taxonomy, MaintenanceRecord[], DueItem[]]) => {
        if (controller.signal.aborted) return;
        setTaxonomy(tax);
        setRecords(list);
        setDueItems(due);
        setLoadError(null);
      })
      .catch((caught: Error) => {
        if (!controller.signal.aborted) {
          setLoadError(caught.message || "Could not load maintenance data.");
        }
      });
    return () => controller.abort();
  }, [activeBike.id, revision]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setLoadError(null);
    try {
      const response = await fetch("/api/maintenance", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          bike_id: activeBike.id,
          service_date: serviceDate,
          system,
          component: selectedComponent,
          component_detail: selectedComponent === "other" ? componentDetail : null,
          action,
          reason,
          performer_type: performerType,
          evidence_type: evidenceType,
          engine_hours: engineHours.trim() ? Number(engineHours) : null,
          engine_hours_is_estimated: true,
          details: details.trim() || null,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        setLoadError(
          body?.error?.message ?? body?.message ?? "Could not save the service.",
        );
        return;
      }
      setComponentDetail("");
      setDetails("");
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: string) {
    if (busy) return;
    setBusy(true);
    try {
      const response = await fetch(`/api/maintenance/${id}`, { method: "DELETE" });
      if (!response.ok) {
        setLoadError("Could not delete the service.");
        return;
      }
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function onAddRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      const response = await fetch("/api/maintenance/rules", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          bike_id: activeBike.id,
          system,
          component: selectedComponent,
          action,
          recurring_interval_hours: Number(ruleHours),
          whichever_comes_first: true,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        setLoadError(body?.error?.message ?? "Could not save rule.");
        return;
      }
      refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="maintenance-workspace">
      <section className="glass-card maintenance-list-card">
        <h3>Due state</h3>
        <p className="maintenance-lede">
          Derived from rules + history. Nothing stores a next-due date.
        </p>
        {dueItems.length === 0 ? (
          <p>No active rules yet. Add an interval below.</p>
        ) : (
          <ul className="maintenance-list">
            {dueItems.map((item) => (
              <li key={item.rule_id}>
                <div>
                  <strong>
                    {item.status.replaceAll("_", " ")} · {item.action}{" "}
                    {item.component.replaceAll("_", " ")}
                  </strong>
                  <span>
                    {item.system}
                    {item.hours_remaining != null
                      ? ` · ${item.hours_remaining.toFixed(1)} h remaining`
                      : ""}
                    {!item.definitive ? " · estimated" : ""}
                  </span>
                  {item.note ? <p>{item.note}</p> : null}
                </div>
              </li>
            ))}
          </ul>
        )}
        <form className="maintenance-form" onSubmit={onAddRule}>
          <label>
            Recurring hours
            <input
              type="number"
              min="0.1"
              step="0.1"
              required
              value={ruleHours}
              onChange={(event) => setRuleHours(event.target.value)}
            />
          </label>
          <button type="submit" disabled={busy || !taxonomy}>
            Add rule for selected system/component/action
          </button>
        </form>
      </section>

      <section className="glass-card maintenance-form-card">
        <h3>Log a service</h3>
        <p className="maintenance-lede">
          Structured history for {activeBike.nickname}. Due dates are calculated later from
          rules — not stored on each record.
        </p>
        <form className="maintenance-form" onSubmit={onSubmit}>
          <label>
            Date
            <input
              type="date"
              required
              value={serviceDate}
              onChange={(event) => setServiceDate(event.target.value)}
            />
          </label>
          <label>
            System
            <select
              value={system}
              onChange={(event) => setSystem(event.target.value)}
              required
            >
              {(taxonomy?.systems ?? []).map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Component
            <select
              value={selectedComponent}
              onChange={(event) => setComponent(event.target.value)}
              required
            >
              {components.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          {selectedComponent === "other" ? (
            <label>
              Component detail
              <input
                value={componentDetail}
                onChange={(event) => setComponentDetail(event.target.value)}
                required
                maxLength={500}
                placeholder="What was serviced?"
              />
            </label>
          ) : null}
          <label>
            Action
            <select
              value={action}
              onChange={(event) => setAction(event.target.value)}
              required
            >
              {(taxonomy?.actions ?? []).map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Reason
            <select
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              required
            >
              {(taxonomy?.reasons ?? []).map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Performer
            <select
              value={performerType}
              onChange={(event) => setPerformerType(event.target.value)}
              required
            >
              {(taxonomy?.performer_types ?? []).map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Evidence
            <select
              value={evidenceType}
              onChange={(event) => setEvidenceType(event.target.value)}
              required
            >
              {(taxonomy?.evidence_types ?? []).map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Engine hours
            <input
              type="number"
              min="0"
              step="0.1"
              value={engineHours}
              onChange={(event) => setEngineHours(event.target.value)}
              placeholder="Optional"
            />
          </label>
          <label className="maintenance-form-wide">
            Notes
            <textarea
              value={details}
              onChange={(event) => setDetails(event.target.value)}
              rows={3}
              maxLength={4000}
              placeholder="Parts, fluids, or anything unusual"
            />
          </label>
          <button type="submit" disabled={busy || !taxonomy}>
            {busy ? "Saving…" : "Save service"}
          </button>
        </form>
        {loadError ? (
          <p role="alert" className="maintenance-error">
            {loadError}
          </p>
        ) : null}
      </section>

      <section className="glass-card maintenance-list-card">
        <h3>Service history</h3>
        {records.length === 0 ? (
          <p>No services logged yet for this bike.</p>
        ) : (
          <ul className="maintenance-list">
            {records.map((record) => (
              <li key={record.id}>
                <div>
                  <strong>
                    {record.service_date} ·{" "}
                    {labelFor(taxonomy?.actions ?? [], record.action)}{" "}
                    {record.component_detail ||
                      labelFor(
                        taxonomy?.systems.find((s) => s.key === record.system)
                          ?.components ?? [],
                        record.component,
                      )}
                  </strong>
                  <span>
                    {labelFor(taxonomy?.systems ?? [], record.system)} ·{" "}
                    {labelFor(taxonomy?.reasons ?? [], record.reason)}
                    {record.engine_hours != null
                      ? ` · ${record.engine_hours} h`
                      : ""}
                  </span>
                  {record.details ? <p>{record.details}</p> : null}
                </div>
                <button
                  type="button"
                  className="maintenance-delete"
                  disabled={busy}
                  onClick={() => void onDelete(record.id)}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
