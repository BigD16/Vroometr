"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useActiveBike } from "@/components/ActiveBikeProvider";
import { readApiError } from "@/lib/api-errors";

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
  const [threads, setThreads] = useState<Conversation[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const refresh = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    if (!activeBike) {
      setThreads([]);
      setDetail(null);
      setSelectedId(null);
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    const query = new URLSearchParams({ bike_id: activeBike.id });
    fetch(`/api/conversations?${query}`, { signal: controller.signal })
      .then(checked)
      .then((response) => response.json())
      .then((items: Conversation[]) => {
        if (controller.signal.aborted) return;
        setThreads(items);
        setLoading(false);
        if (selectedId && !items.some((item) => item.id === selectedId)) {
          setSelectedId(null);
          setDetail(null);
        }
      })
      .catch((caught: Error) => {
        if (!controller.signal.aborted) {
          setError(caught.message);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [activeBike, revision, selectedId]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    const controller = new AbortController();
    fetch(`/api/conversations/${selectedId}`, { signal: controller.signal })
      .then(checked)
      .then((response) => response.json())
      .then((payload: Detail) => {
        if (!controller.signal.aborted) setDetail(payload);
      })
      .catch((caught: Error) => {
        if (!controller.signal.aborted) setError(caught.message);
      });
    return () => controller.abort();
  }, [selectedId, revision]);

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
    if (!activeBike) return;
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
    });
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    if (!selectedId || !draft.trim()) return;
    const content = draft.trim();
    await action(async () => {
      await checked(
        await fetch(`/api/conversations/${selectedId}/messages`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ content, role: "user" }),
        }),
      );
      setDraft("");
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
    });
  }

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
                onClick={() => setSelectedId(thread.id)}
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
            Create or open a thread. User messages are stored now; agent replies arrive in later
            Phase 5 work.
          </p>
        ) : null}

        {detail ? (
          <>
            <div className="assistant-thread-controls">
              <label>
                Bike context
                <select
                  value={detail.conversation.current_bike_id}
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
            <p className="assistant-note">
              Messages are saved. There is no agent reply yet—only conversation storage.
            </p>
            <div className="chat" aria-live="polite">
              {detail.messages.length === 0 ? (
                <p className="placeholder-copy">No messages yet. Send one below.</p>
              ) : null}
              {detail.messages.map((message) => (
                <article key={message.id} className={`chat-message role-${message.role}`}>
                  <small>{message.role}</small>
                  <p>{message.content}</p>
                </article>
              ))}
              {detail.boundaries.length > 0 ? (
                <p className="assistant-boundaries">
                  {detail.boundaries.length} bike-context{" "}
                  {detail.boundaries.length === 1 ? "boundary" : "boundaries"} recorded in this
                  thread.
                </p>
              ) : null}
              {detail.conversation.rolling_summary ? (
                <details className="assistant-summary">
                  <summary>Rolling summary</summary>
                  <pre>{detail.conversation.rolling_summary}</pre>
                </details>
              ) : null}
            </div>
            <form className="composer" onSubmit={(event) => void sendMessage(event)}>
              <button type="button" aria-label="Add" disabled>
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
