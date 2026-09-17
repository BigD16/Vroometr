"use client";

import { useEffect, useState } from "react";

type Page = {
  page_index: number; state: string; processing_class: string;
  text_excerpt: string; text_truncated: boolean; error_code: string | null;
};
type Status = {
  ingestion: { state: string; page_count: number; error_code: string | null;
    retry_after: string | null } | null;
  pages: Page[];
};

export function DocumentIngestion({ documentId }: { documentId: string }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [checkedAt, setCheckedAt] = useState(0);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function load() {
      try {
        const response = await fetch(`/api/documents/${documentId}/ingestion`, { signal: controller.signal });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error?.message ?? "Could not load extraction status.");
        if (controller.signal.aborted) return;
        setStatus(data); setCheckedAt(Date.now()); setError(null);
        if (["queued", "running"].includes(data.ingestion?.state)) timer = setTimeout(load, 3000);
      } catch (caught) {
        if (!controller.signal.aborted) {
          setStatus(null);
          setError(caught instanceof Error ? caught.message : "Could not load extraction status.");
        }
      }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [documentId, revision]);

  async function run() {
    setBusy(true); setError(null);
    try {
      const response = await fetch(`/api/documents/${documentId}/ingestion`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message ?? "Could not queue extraction.");
      setStatus(previous => ({ ingestion: data, pages: previous?.pages ?? [] }));
      setRevision(value => value + 1);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not queue extraction.");
    } finally { setBusy(false); }
  }

  const job = status?.ingestion;
  const waiting = !!job && ["queued", "running"].includes(job.state);
  const canRetry = !waiting || !job?.retry_after || checkedAt >= Date.parse(job.retry_after);
  const label = job?.state === "partial" ? "Partially extracted" : job?.state === "completed"
    ? "Text extraction complete" : job ? `Extraction ${job.state}` : "Not extracted";
  return <section aria-label="Document extraction">
    {error ? <p role="alert">{error}</p> : null}
    <p role="status">{!status && !error ? "Loading extraction status…" : label}</p>
    {job?.error_code ? <p>{job.error_code === "source_changed"
      ? "The file changed since registration. Register an unchanged copy."
      : job.error_code === "queue_unavailable" ? "Could not start extraction. Retry when the service is available."
      : "Extraction failed. Check the file and retry."}</p> : null}
    <button disabled={busy || !status || !canRetry} onClick={() => void run()}>
      {busy ? "Queuing…" : job ? "Retry incomplete pages" : "Extract pages"}
    </button>
    <button disabled={busy} onClick={() => setRevision(value => value + 1)}>Refresh extraction</button>
    {waiting && job?.retry_after ? <p>Retry is available after {new Date(job.retry_after).toLocaleString()} if extraction stalls.</p> : null}
    {status?.pages.length ? <details>
      <summary>Review extracted pages ({status.pages.length} / {job?.page_count ?? 0})</summary>
      <ul>{status.pages.map(page => <li key={page.page_index}>
        <strong>Page {page.page_index + 1}</strong>
        <p>{page.state === "pending_provider" ? "Needs OCR/vision — provider pending"
          : page.state === "failed" ? "Page extraction failed — retry available" : "Text extracted"}</p>
        {page.text_excerpt ? <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{page.text_excerpt}</pre> : null}
        {page.text_truncated ? <p>Showing an excerpt. The full extracted text is saved.</p> : null}
      </li>)}</ul>
    </details> : null}
  </section>;
}
