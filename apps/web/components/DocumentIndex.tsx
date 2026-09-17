"use client";

import { useEffect, useState } from "react";

type Section = { id: string; parent_section_id: string | null; section_title: string;
  start_page: number; end_page: number; source_method: string };
type Chunk = { id: string; section_id: string; chunk_index: number; page_start: number;
  cleaned_text: string; content_type: string; embedded: boolean;
  source_span: { start_char: number; end_char: number }[] };
type Status = { indexing: { state: string; retry_after: string | null; error_code: string | null } | null;
  stale: boolean; sections: Section[]; chunks: Chunk[]; total_chunks: number; embedded_chunks: number };

export function DocumentIndex({ documentId }: { documentId: string }) {
  const [data, setData] = useState<Status | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [checkedAt, setCheckedAt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function load() {
      try {
        const response = await fetch(`/api/documents/${documentId}/index?offset=${offset}&limit=20`, { signal: controller.signal });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error?.message ?? "Could not load sections and chunks.");
        if (controller.signal.aborted) return;
        setData(result); setError(null); setCheckedAt(Date.now());
        if (!result.stale && ["queued", "running"].includes(result.indexing?.state)) timer = setTimeout(load, 3000);
      } catch (caught) {
        if (!controller.signal.aborted) {
          setData(null); setError(caught instanceof Error ? caught.message : "Could not load document index.");
        }
      }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [documentId, offset, revision]);

  async function build() {
    setBusy(true); setError(null);
    try {
      const response = await fetch(`/api/documents/${documentId}/index`, { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error?.message ?? "Could not queue document indexing.");
      setData(previous => previous ? { ...previous, indexing: result, stale: false } : null);
      setOffset(0); setRevision(value => value + 1);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not queue document indexing.");
    } finally { setBusy(false); }
  }
  const job = data?.indexing;
  const waiting = !!job && !data?.stale && ["queued", "running"].includes(job.state);
  const canRetry = !waiting || !job?.retry_after || checkedAt >= Date.parse(job.retry_after);
  const labels: Record<string, string> = { queued: "Indexing queued", running: "Building document index",
    completed: "Sections and embeddings ready", partial: "Index built from available text; some content is incomplete",
    failed: "Indexing failed", awaiting_configuration: "Sections saved; embedding service needs configuration" };
  return <section aria-label="Sections and chunks">
    <h4>Sections and chunks</h4>
    <p>Extract pages first. Building embeddings sends completed-page text to the configured embedding provider.</p>
    <p role="status">{data?.stale ? "This index is out of date. Rebuild it after extraction finishes."
      : job ? labels[job.state] ?? job.state : data ? "No document index yet" : error ? "Index unavailable" : "Loading document index…"}</p>
    {error ? <p role="alert">{error}</p> : null}
    {job?.error_code && job.state !== "awaiting_configuration" ? <p>{job.error_code === "source_changed"
      ? "The PDF changed. Register an unchanged copy."
      : "The operation could not finish. Saved results are retained; retry when the service is available."}</p> : null}
    <button disabled={busy || !data || !canRetry} onClick={() => void build()}>
      {busy ? "Queuing…" : job ? "Rebuild / retry embeddings" : "Build sections & embeddings"}
    </button>
    <button disabled={busy} onClick={() => setRevision(value => value + 1)}>Refresh index</button>
    {data && data.sections.length > 0 ? <details>
      <summary>Review sections and chunks ({data.embedded_chunks}/{data.total_chunks} embedded)</summary>
      <ul>{data.sections.map(section => <li key={section.id}>
        <strong>{section.section_title}</strong>
        {section.parent_section_id ? <span> — within {data.sections.find(s => s.id === section.parent_section_id)?.section_title}</span> : null}
        <span> · pages {section.start_page + 1}–{section.end_page + 1}</span>
        {section.source_method === "page_fallback" ? <span> · Page grouping</span> : null}
        {section.source_method === "numbered_heading_heuristic" ? <span> · Detected heading</span> : null}
      </li>)}</ul>
      {data.chunks.map(chunk => <article key={chunk.id}>
        <h5>Chunk {chunk.chunk_index + 1} · Page {chunk.page_start + 1} · {chunk.embedded ? "Embedded" : "Embedding pending"}</h5>
        <p>{data.sections.find(s => s.id === chunk.section_id)?.section_title} · {chunk.content_type.replaceAll("_", " ")}</p>
        <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{chunk.cleaned_text}</pre>
        <small>Source characters {chunk.source_span[0]?.start_char}–{chunk.source_span[0]?.end_char} (end exclusive)</small>
      </article>)}
      <button disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - 20))}>Previous chunks</button>
      <button disabled={offset + 20 >= data.total_chunks} onClick={() => setOffset(value => value + 20)}>Next chunks</button>
    </details> : null}
  </section>;
}
