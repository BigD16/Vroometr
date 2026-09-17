"use client";

import { useEffect, useRef, useState } from "react";

type Passage = { id: string; document_id: string; attachment_id: string; file_name: string;
  section_title: string; page_start: number; text: string; document_type: string;
  document_revision: number; is_primary: boolean; document_status: string; incomplete: boolean };
type Match = { passage: Passage; role: string; confidence: number };
type Result = { status: string; passages: Match[]; include_reference_editions: boolean };

export function DocumentSearch({ bikeId }: { bikeId: string }) {
  const [query, setQuery] = useState("");
  const [references, setReferences] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<{ id: string; url: string } | null>(null);
  const [sourceBusy, setSourceBusy] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);
  const accessRequest = useRef<AbortController | null>(null);
  useEffect(() => () => { request.current?.abort(); accessRequest.current?.abort(); }, [bikeId]);

  async function search(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    request.current?.abort(); accessRequest.current?.abort();
    const controller = new AbortController(); request.current = controller;
    setBusy(true); setError(null); setResult(null); setSource(null); setSourceBusy(null);
    try {
      const response = await fetch("/api/retrieval", { method: "POST", signal: controller.signal,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ bike_id: bikeId, query, include_reference_editions: references }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message ?? "Search could not finish. Please retry.");
      if (!controller.signal.aborted) setResult(data);
    } catch (caught) {
      if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : "Search unavailable.");
    } finally { if (!controller.signal.aborted) setBusy(false); }
  }

  async function prepareSource(passage: Passage) {
    accessRequest.current?.abort();
    const controller = new AbortController(); accessRequest.current = controller;
    setSourceBusy(passage.id); setSource(null); setError(null);
    try {
      const response = await fetch(`/api/attachments/${passage.attachment_id}/access?download=false`,
        { signal: controller.signal, cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message ?? "Could not open this source. Search again.");
      if (!controller.signal.aborted) setSource({ id: passage.id, url: `${data.url}#page=${passage.page_start + 1}` });
    } catch (caught) {
      if (!controller.signal.aborted) {
        setResult(null);
        setError(caught instanceof Error ? caught.message : "Source unavailable. Search again.");
      }
    } finally { if (!controller.signal.aborted) setSourceBusy(null); }
  }

  const empty: Record<string, string> = {
    no_indexed_sources: "No searchable documents in this scope. Confirm a manual or supporting document, extract its pages, and build its embeddings below.",
    no_relevant_evidence: "No relevant source passages found. Try a different search or add a matching document.",
    sources_changed: "Documents changed during search. Search again for current results.",
  };
  return <section className="glass-card document-library" aria-label="Search bike documents">
    <h2>Search bike documents</h2>
    <p>Search the primary manual and active supporting documents. Your query and matching excerpts are sent to the search providers.</p>
    <form onSubmit={event => void search(event)}>
      <label htmlFor="document-search-query">What are you looking for?</label>
      <input id="document-search-query" type="search" required maxLength={1200} value={query}
        onChange={event => setQuery(event.target.value)} placeholder="A component, procedure, or manual topic" />
      <label><input type="checkbox" checked={references} onChange={event => setReferences(event.target.checked)} />
        Include other confirmed editions and archived documents</label>
      <button type="submit" disabled={busy || !query.trim()}>{busy ? "Searching…" : "Search documents"}</button>
    </form>
    {busy ? <p role="status">Finding relevant source passages…</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    {result && result.status !== "ready" ? <p role="status">{empty[result.status] ?? "No passages available. Search again."}</p> : null}
    {result?.status === "ready" ? <div>
      <p role="status">{result.passages.length} source passages · {result.include_reference_editions ? "Including reference editions" : "Primary manual and active supporting documents"}</p>
      <p>These are source excerpts. Check the full procedure and document applicability before using them. Match strength is a search estimate.</p>
      {result.passages.map(({ passage, role, confidence }) => <article key={passage.id}>
        <h3>{passage.section_title} · Page {passage.page_start + 1}</h3>
        <p>{passage.file_name} · Revision {passage.document_revision} · {passage.document_type.replaceAll("_", " ")}
          {passage.is_primary ? " · Primary manual" : ""}{passage.document_status === "archived" ? " · Archived reference" : ""}</p>
        <small>{role === "neighbor" ? "Adjacent context" : `Match strength: ${confidence >= 0.75 ? "High" : confidence >= 0.5 ? "Moderate" : "Low"}`}</small>
        {passage.incomplete ? <p>This document is only partly searchable; some pages or embeddings are unavailable.</p> : null}
        <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{passage.text}</pre>
        <button disabled={sourceBusy === passage.id} onClick={() => void prepareSource(passage)}>
          {sourceBusy === passage.id ? "Preparing PDF…" : "View source PDF"}</button>
        {source?.id === passage.id ? <p><a href={source.url} target="_blank" rel="noopener noreferrer">Open PDF at page {passage.page_start + 1}</a> · Link expires after 60 seconds; prepare it again if needed.</p> : null}
      </article>)}
    </div> : null}
  </section>;
}
