"use client";

import Link from "next/link";

import { useActiveBike } from "@/components/ActiveBikeProvider";

export function AssistantFab() {
  const { activeBike } = useActiveBike();
  const machineName = activeBike?.nickname ?? "your machine";

  return (
    <Link className="assistant-fab" href="/assistant">
      <span>✦</span>
      <div>
        <small>VROOMETR ASSISTANT</small>
        <b>Ask about {machineName}…</b>
      </div>
      <em>↑</em>
    </Link>
  );
}
