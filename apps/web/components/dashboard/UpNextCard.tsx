"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { Bike } from "@/lib/bikes";

type DueItem = {
  system: string;
  component: string;
  action: string;
  status: string;
  definitive: boolean;
  hours_remaining: number | null;
  days_remaining: number | null;
  note: string | null;
};

export function UpNextCard({ bike }: { bike: Bike | null }) {
  const [items, setItems] = useState<DueItem[]>([]);

  useEffect(() => {
    if (!bike) return;
    const controller = new AbortController();
    fetch(`/api/maintenance/due-state?bike_id=${encodeURIComponent(bike.id)}`, {
      signal: controller.signal,
    })
      .then((response) => (response.ok ? response.json() : []))
      .then((rows: DueItem[]) => {
        if (!controller.signal.aborted) {
          setItems(
            rows
              .filter((row) =>
                ["overdue", "due_soon", "never_serviced"].includes(row.status),
              )
              .slice(0, 4),
          );
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setItems([]);
      });
    return () => controller.abort();
  }, [bike]);

  return (
    <article className="glass-card">
      <header>
        <span>UP NEXT</span>
        <Link className="dashboard-card-link" href="/maintenance">
          VIEW ALL →
        </Link>
      </header>
      {bike === null || items.length === 0 ? (
        <div className="dashboard-card-empty">
          <span aria-hidden="true">◇</span>
          <div>
            <b>{bike === null ? "No active machine" : "No due tasks yet"}</b>
            <p>
              {bike === null
                ? "Add a bike before building a maintenance plan."
                : "Add an interval rule on Maintenance to derive due state."}
            </p>
          </div>
        </div>
      ) : (
        <ul className="dashboard-due-list">
          {items.map((item) => (
            <li key={`${item.system}-${item.component}-${item.action}`}>
              <b>
                {item.action} {item.component.replaceAll("_", " ")}
              </b>
              <span>
                {item.status.replaceAll("_", " ")}
                {!item.definitive ? " (est.)" : ""}
                {item.hours_remaining != null
                  ? ` · ${item.hours_remaining.toFixed(1)} h`
                  : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
