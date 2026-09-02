import Link from "next/link";

import { mockMachine } from "@/lib/mock-machine";

export function AssistantFab() {
  return (
    <Link className="assistant-fab" href="/assistant">
      <span>✦</span>
      <div>
        <small>VROOMETR ASSISTANT</small>
        <b>Ask about {mockMachine.nickname}…</b>
      </div>
      <em>↑</em>
    </Link>
  );
}
