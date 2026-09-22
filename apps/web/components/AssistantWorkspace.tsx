"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useActiveBike } from "@/components/ActiveBikeProvider";
import {
  AssistantSources,
  type AssistantCitation,
} from "@/components/AssistantSources";
import { readApiError } from "@/lib/api-errors";
import type { Bike } from "@/lib/bikes";

type Conversation = {
  id: string;
  initial_bike_id: string;
  current_bike_id: string;
  status: string;
  rolling_summary: string | null;
  summary_model_version: string | null;
  updated_at: string;
};

type Message = {
  id: string;
  role: string;
  content: string;
  bike_context_id: string;
  created_at: string;
  /** Present when a future agent answer includes citation payloads (5.5). */
  citations?: AssistantCitation[] | null;
};

type Boundary = {
  id: string;
  from_bike_id: string;
  to_bike_id: string;
  message_id: string | null;
};

type Detail = {
  conversation: Conversation;
  messages: Message[];
  boundaries: Boundary[];
};

type CompactContext = {
  version: string;
  bike: {
    nickname: string;
    make: string;
    model: string;
    year: number;
    powertrain_type: string;
    stroke_type: string | null;
    current_engine_hours: number | null;
    current_engine_hours_is_estimated: boolean;
  };
  conversation: {
    recent_turns: Message[];
    rolling_summary: string | null;
    boundary_count: number;
  };
  modifications: { available: boolean; reason: string | null };
  maintenance: { available: boolean; reason: string | null };
  ride: { available: boolean; reason: string | null };
  budget: {
    recent_turns_included: number;
    recent_turns_omitted: number;
    recent_chars_used: number;
    summary_chars: number;
  };
};

async function checked(response: Response): Promise<Response> {
  if (!response.ok) {
    throw new Error(await readApiError(response, "Could not complete this action."));
  }
  return response;
}

function threadLabel(conversation: Conversation, index: number): string {
  if (conversation.rolling_summary) {
    const firstLine = conversation.rolling_summary.split("\n")[0]?.trim() ?? "";
    if (firstLine) {
      return firstLine.length > 48 ? `${firstLine.slice(0, 45)}…` : firstLine;
    }
  }
  return `Conversation ${index + 1}`;
}

export function AssistantWorkspace() {
  const { activeBike, bikes, state, error: bikeError, reload } = useActiveBike();

  if (state === "loading") {
    return <p className="placeholder-copy" role="status">Loading bike context…</p>;
  }

  if (!activeBike) {
    return (
      <div className="assistant-empty">
        <p className="placeholder-copy">
          Select an active bike to start a conversation. Threads are bike-scoped by default.
        </p>
        {bikeError ? (
          <button type="button" onClick={() => void reload()}>
            Retry bike load
          </button>
        ) : null}
      </div>
    );
  }

  return (
    <AssistantBikeWorkspace key={activeBike.id} activeBike={activeBike} bikes={bikes} />
  );
}

function AssistantBikeWorkspace({
  activeBike,
  bikes,
}: {
  activeBike: Bike;
  bikes: Bike[];
}) {
  const [threads, setThreads] = useState<Conversation[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [contextPack, setContextPack] = useState<CompactContext | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const refresh = useCallback(() => setRevision((value) => value + 1), []);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ bike_id: activeBike.id });
    fetch(`/api/conversations?${query}`, { signal: controller.signal })
      .then(checked)
      .then((response) => response.json())
      .then((items: Conversation[]) => {
        if (controller.signal.aborted) return;
        setThreads(items);
        setLoading(false);
        setSelectedId((current) =>
          current && !items.some((item) => item.id === current) ? null : current,
        );
      })
      .catch((caught: Error) => {
        if (!controller.signal.aborted) {
          setError(caught.message);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [activeBike.id, revision]);

  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController();
    const conversationId = selectedId;
    Promise.all([
      fetch(`/api/conversations/${conversationId}`, { signal: controller.signal })
        .then(checked)
        .then((response) => response.json()),
      fetch(`/api/conversations/${conversationId}/context`, { signal: controller.signal })
        .then(checked)
        .then((response) => response.json()),
    ])
      .then(([payload, pack]: [Detail, CompactContext]) => {
        if (!controller.signal.aborted) {
          setDetail(payload);
          setContextPack(pack);
        }
      })
      .catch((caught: Error) => {
        if (!controller.signal.aborted) setError(caught.message);
      });
    return () => controller.abort();
  }, [selectedId, revision]);

  const activeDetail =
    selectedId && detail?.conversation.id === selectedId ? detail : null;
  const activeContextPack = activeDetail ? contextPack : null;

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ block: "end" });
  }, [activeDetail?.messages.length, selectedId]);

  async function action(operation: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await operation();
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Action failed.");
    } finally {
      setBusy(false);
    }
  }

  async function createThread() {
    await action(async () => {
      const response = await checked(
        await fetch("/api/conversations", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ bike_id: activeBike.id }),
        }),
      );
      const created = (await response.json()) as Conversation;
      setSelectedId(created.id);
      setDetail(null);
      setContextPack(null);
    });
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    if (!selectedId || !draft.trim()) return;
    const content = draft.trim();
    await action(async () => {
      const response = await checked(
        await fetch(`/api/conversations/${selectedId}/messages`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ content, role: "user" }),
        }),
      );
      const payload = (await response.json()) as {
        assistant_status?: string | null;
        assistant_error?: string | null;
      };
      setDraft("");
      if (payload.assistant_status === "awaiting_configuration") {
        setError(
          "Assistant model is not configured yet. Your message was saved; set AGENT_MODEL and OpenAI settings to enable replies.",
        );
      } else if (payload.assistant_status === "failed") {
        setError(payload.assistant_error || "Assistant could not complete a reply.");
      }
    });
  }

  async function switchBike(bikeId: string) {
    if (!selectedId || !bikeId) return;
    await action(async () => {
      const response = await checked(
        await fetch(`/api/conversations/${selectedId}/bike`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ bike_id: bikeId }),
        }),
      );
      setDetail((await response.json()) as Detail);
    });
  }

  async function deleteThread() {
    if (!selectedId) return;
    await action(async () => {
      await checked(await fetch(`/api/conversations/${selectedId}`, { method: "DELETE" }));
      setSelectedId(null);
      setDetail(null);
      setContextPack(null);
    });
  }

  function selectThread(threadId: string) {
    setSelectedId(threadId);
    setDetail(null);
    setContextPack(null);
  }

  return (
    <div className="assistant-workspace">
      <aside className="assistant-threads" aria-label="Conversations">
        <div className="assistant-threads-header">
          <h3>Threads</h3>
          <button type="button" disabled={busy} onClick={() => void createThread()}>
            New
          </button>
        </div>
        {loading ? <p role="status">Loading conversations…</p> : null}
        {!loading && threads.length === 0 ? (
          <p className="placeholder-copy">No conversations yet for {activeBike.nickname}.</p>
        ) : null}
        <ul>
          {threads.map((thread, index) => (
            <li key={thread.id}>
              <button
                type="button"
                className={thread.id === selectedId ? "is-active" : undefined}
                onClick={() => selectThread(thread.id)}
              >
                {threadLabel(thread, index)}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <div className="assistant-main">
        {error ? (
          <div role="alert" className="assistant-alert">
            <p>{error}</p>
            <button type="button" onClick={() => { setError(null); refresh(); }}>
              Retry
            </button>
          </div>
        ) : null}

        {!selectedId ? (
          <p className="placeholder-copy">
            Create or open a thread to ask about {activeBike.nickname}. Messages are saved now;
            cited assistant replies arrive with the agent loop.
          </p>
        ) : null}

        {activeDetail ? (
          <>
            <div className="assistant-thread-controls">
              <label>
                Bike context
                <select
                  value={activeDetail.conversation.current_bike_id}
                  disabled={busy}
                  onChange={(event) => void switchBike(event.target.value)}
                >
                  {bikes.map((bike) => (
                    <option key={bike.id} value={bike.id}>
                      {bike.nickname}
                    </option>
                  ))}
                </select>
              </label>
              <button type="button" disabled={busy} onClick={() => void deleteThread()}>
                Delete thread
              </button>
            </div>
            {activeContextPack ? (
              <details className="assistant-context-pack">
                <summary>Always-loaded context</summary>
                <p>
                  {activeContextPack.bike.year} {activeContextPack.bike.make}{" "}
                  {activeContextPack.bike.model} ({activeContextPack.bike.nickname}) ·{" "}
                  {activeContextPack.bike.powertrain_type}
                  {activeContextPack.bike.stroke_type
                    ? ` · ${activeContextPack.bike.stroke_type}`
                    : ""}
                  {activeContextPack.bike.current_engine_hours != null
                    ? ` · ${activeContextPack.bike.current_engine_hours}h${
                        activeContextPack.bike.current_engine_hours_is_estimated ? " est." : ""
                      }`
                    : ""}
                </p>
                <p>
                  Recent turns: {activeContextPack.budget.recent_turns_included} included
                  {activeContextPack.budget.recent_turns_omitted > 0
                    ? `, ${activeContextPack.budget.recent_turns_omitted} omitted`
                    : ""}{" "}
                  · {activeContextPack.budget.recent_chars_used} chars · summary{" "}
                  {activeContextPack.budget.summary_chars} chars
                </p>
                <p>
                  Mods/maintenance/rides: not available yet (
                  {activeContextPack.modifications.reason ?? "domain_not_implemented"}).
                </p>
              </details>
            ) : null}
            <div className="chat" aria-live="polite">
              {activeDetail.messages.length === 0 ? (
                <p className="placeholder-copy">No messages yet. Ask something below.</p>
              ) : null}
              {activeDetail.messages.map((message) => (
                <article key={message.id} className={`chat-message role-${message.role}`}>
                  <small>{message.role}</small>
                  <p>{message.content}</p>
                  {message.citations && message.citations.length > 0 ? (
                    <AssistantSources citations={message.citations} />
                  ) : null}
                </article>
              ))}
              {activeDetail.boundaries.length > 0 ? (
                <p className="assistant-boundaries">
                  {activeDetail.boundaries.length} bike-context{" "}
                  {activeDetail.boundaries.length === 1 ? "boundary" : "boundaries"} recorded in this
                  thread.
                </p>
              ) : null}
              {activeDetail.conversation.rolling_summary ? (
                <details className="assistant-summary">
                  <summary>Rolling summary</summary>
                  <pre>{activeDetail.conversation.rolling_summary}</pre>
                </details>
              ) : null}
              <div ref={chatEndRef} />
            </div>
            <form className="composer" onSubmit={(event) => void sendMessage(event)}>
              <button type="button" aria-label="Add attachment" title="Attachments come later" disabled>
                ＋
              </button>
              <input
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder={`Message Vroometr about ${activeBike.nickname}…`}
                aria-label="Message"
                disabled={busy}
              />
              <button type="submit" className="send" aria-label="Send" disabled={busy || !draft.trim()}>
                ↑
              </button>
            </form>
          </>
        ) : null}
      </div>
    </div>
  );
}
