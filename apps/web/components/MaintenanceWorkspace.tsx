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

type RuleRow = {
  id: string;
  system: string;
  component: string;
  action: string;
  validation_status: string;
  active: boolean;
  rule_version: number;
  recurring_interval_hours: number | null;
  source_span: string | null;
  source_page: number | null;
};

type BaselineRec = {
  rule_id: string;
  system: string;
  component: string;
  action: string;
  status: string;
  priority: string;
  summary: string;
  manufacturer_recurring_interval_hours: number | null;
  definitive: boolean;
};

type ContextualRec = {
  rule_id: string;
  advice: string;
  consider_earlier: boolean;
  source: string;
  context_tags: string[];
};

type RecommendationBundle = {
  baseline: BaselineRec[];
  contextual: ContextualRec[];
  manufacturer_intervals_unchanged: boolean;
  note: string | null;
};

const CONTEXT_TAG_OPTIONS = [
  "dust",
  "sand",
  "mud",
  "wet",
  "race",
  "upcoming_ride",
  "modification",
  "symptom",
] as const;

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
  const [planRules, setPlanRules] = useState<RuleRow[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationBundle | null>(
    null,
  );
  const [contextTags, setContextTags] = useState<string[]>([]);
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
  const [hoursEstimated, setHoursEstimated] = useState(true);
  const [syncBikeHours, setSyncBikeHours] = useState(false);
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
    const tagQuery =
      contextTags.length > 0
        ? `&context_tags=${encodeURIComponent(contextTags.join(","))}`
        : "";
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
      fetch(
        `/api/maintenance/rules?bike_id=${encodeURIComponent(activeBike.id)}&include_inactive=true`,
        { signal: controller.signal },
      ).then((response) => (response.ok ? response.json() : [])),
      fetch(
        `/api/maintenance/recommendations?bike_id=${encodeURIComponent(activeBike.id)}${tagQuery}`,
        { signal: controller.signal },
      ).then((response) => (response.ok ? response.json() : null)),
    ])
      .then(
        ([tax, list, due, rules, recs]: [
          Taxonomy,
          MaintenanceRecord[],
          DueItem[],
          RuleRow[],
          RecommendationBundle | null,
        ]) => {
          if (controller.signal.aborted) return;
          setTaxonomy(tax);
          setRecords(list);
          setDueItems(due);
          setPlanRules(rules.filter((row) => row.active));
          setRecommendations(recs);
          setLoadError(null);
        },
      )
      .catch((caught: Error) => {
        if (!controller.signal.aborted) {
          setLoadError(caught.message || "Could not load maintenance data.");
        }
      });
    return () => controller.abort();
  }, [activeBike.id, revision, contextTags]);

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
          engine_hours_is_estimated: hoursEstimated,
          sync_bike_hours: syncBikeHours && Boolean(engineHours.trim()),
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

  async function onRebuildPlan() {
    if (busy) return;
    setBusy(true);
    setLoadError(null);
    try {
      const response = await fetch("/api/maintenance/rules/extract", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          bike_id: activeBike.id,
          force: true,
        }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        setLoadError(
          body?.error?.message ??
            "Could not build the plan. Confirm a manufacturer manual first.",
        );
        return;
      }
      const accepted = Array.isArray(body?.accepted) ? body.accepted.length : 0;
      const rejected = Array.isArray(body?.rejected) ? body.rejected.length : 0;
      if (body?.skipped && body?.reason === "already_extracted") {
        setLoadError("Plan already built from this manual. Forced rebuild kept existing rules.");
      } else if (accepted === 0) {
        setLoadError(
          rejected > 0
            ? `No rules passed validation (${rejected} rejected). Try Rebuild again.`
            : "No validated intervals found in the manual yet.",
        );
      } else {
        setLoadError(null);
      }
      refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="maintenance-workspace">
      <section className="glass-card maintenance-list-card">
        <h3>Maintenance plan</h3>
        <p className="maintenance-lede">
          Built automatically from your manufacturer manual after pages are extracted.
          Due dates are derived — nothing stores a next-due date.
        </p>
        {planRules.length === 0 ? (
          <p>
            No plan yet. Confirm and extract a manufacturer manual in Documents, or rebuild
            below once pages are ready.
          </p>
        ) : (
          <ul className="maintenance-list">
            {planRules.map((rule) => (
              <li key={rule.id}>
                <div>
                  <strong>
                    {rule.action} {rule.component.replaceAll("_", " ")}
                  </strong>
                  <span>
                    {rule.system}
                    {rule.recurring_interval_hours != null
                      ? ` · every ${rule.recurring_interval_hours} h`
                      : ""}
                    {rule.source_page != null ? ` · p.${rule.source_page}` : ""}
                  </span>
                  {rule.source_span ? <p>{rule.source_span}</p> : null}
                </div>
              </li>
            ))}
          </ul>
        )}
        <button type="button" disabled={busy} onClick={() => void onRebuildPlan()}>
          Rebuild plan from manual
        </button>

        <h3>Due state</h3>
        {dueItems.length === 0 ? (
          <p>Nothing due until the plan has active rules and service history.</p>
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

        <h3>Recommendations</h3>
        <p className="maintenance-lede">
          Baseline follows manufacturer intervals. Context tags may urge earlier action —
          they never rewrite those intervals.
        </p>
        <div className="maintenance-form">
          {CONTEXT_TAG_OPTIONS.map((tag) => {
            const checked = contextTags.includes(tag);
            return (
              <label key={tag}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() =>
                    setContextTags((current) =>
                      checked
                        ? current.filter((item) => item !== tag)
                        : [...current, tag],
                    )
                  }
                />{" "}
                {tag.replaceAll("_", " ")}
              </label>
            );
          })}
        </div>
        {recommendations?.note ? <p>{recommendations.note}</p> : null}
        {recommendations && recommendations.baseline.length > 0 ? (
          <ul className="maintenance-list">
            {recommendations.baseline
              .filter((item) => item.priority !== "monitor")
              .map((item) => (
                <li key={`base-${item.rule_id}`}>
                  <div>
                    <strong>
                      Baseline · {item.priority.replaceAll("_", " ")} · {item.action}{" "}
                      {item.component.replaceAll("_", " ")}
                    </strong>
                    <span>{item.summary}</span>
                  </div>
                </li>
              ))}
            {recommendations.contextual.map((item) => (
              <li key={`ctx-${item.rule_id}-${item.source}`}>
                <div>
                  <strong>
                    Context · {item.consider_earlier ? "consider earlier" : "note"}
                  </strong>
                  <span>{item.advice}</span>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p>No recommendations until the plan has active rules.</p>
        )}

        <form className="maintenance-form" onSubmit={onAddRule}>
          <label>
            Manual override · recurring hours
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
          <label>
            <input
              type="checkbox"
              checked={hoursEstimated}
              onChange={(event) => setHoursEstimated(event.target.checked)}
            />{" "}
            Hours are estimated (unchecked = confirmed meter)
          </label>
          <label>
            <input
              type="checkbox"
              checked={syncBikeHours}
              onChange={(event) => setSyncBikeHours(event.target.checked)}
              disabled={!engineHours.trim()}
            />{" "}
            Also update bike current hours
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
