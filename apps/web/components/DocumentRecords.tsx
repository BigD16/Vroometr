"use client";

import { DocumentIndex } from "./DocumentIndex";
import { DocumentIngestion } from "./DocumentIngestion";

import { useEffect, useState, type FormEvent } from "react";
import { readApiError } from "@/lib/api-errors";
import type { Bike } from "@/lib/bikes";

type Metadata = { document_type: string; make: string; model: string; year: number };
type DocumentRecord = Metadata & {
  id: string; attachment_id: string; status: string; is_primary: boolean;
  version_group_id: string; revision: number; confirmed_at: string | null;
};
type FileOption = { id: string; file_name: string; status: string; mime_type: string };

async function read(response: Response) {
  if (!response.ok) throw new Error(await readApiError(response, "Could not update documents."));
  return response.json();
}

export function DocumentRecords({ bike, filesRevision = 0 }: { bike: Bike; filesRevision?: number }) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [files, setFiles] = useState<FileOption[]>([]);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editing, setEditing] = useState<DocumentRecord | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetch(`/api/documents?bike_id=${encodeURIComponent(bike.id)}`, { signal: controller.signal }).then(read),
      fetch("/api/attachments", { signal: controller.signal }).then(read),
    ]).then(([records, uploaded]: [DocumentRecord[], FileOption[]]) => {
      if (!controller.signal.aborted) {
        setDocuments(records); setFiles(uploaded); setLoading(false);
      }
    }).catch(caught => {
      if (!controller.signal.aborted) { setError(caught.message); setLoading(false); }
    });
    return () => controller.abort();
  }, [bike.id, revision, filesRevision]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(null); setNotice(null);
    const values = new FormData(event.currentTarget);
    const metadata: Metadata = {
      document_type: String(values.get("document_type")), make: String(values.get("make")),
      model: String(values.get("model")), year: Number(values.get("year")),
    };
    try {
      if (editing) {
        await read(await fetch(`/api/documents/${editing.id}/confirm`, { method: "POST",
          headers: { "content-type": "application/json" }, body: JSON.stringify(metadata) }));
        setNotice("Metadata confirmed. Manufacturer manuals become this bike’s primary manual.");
        setEditing(null);
      } else {
        const result = await read(await fetch("/api/documents", { method: "POST",
          headers: { "content-type": "application/json" }, body: JSON.stringify({ ...metadata,
            bike_id: bike.id, attachment_id: values.get("attachment_id"),
            supersedes_document_id: values.get("supersedes") || null,
          }) }));
        setNotice(result.warning ?? "Document registered. Review and confirm its metadata below.");
        setEditing(result.document);
      }
      setRevision(value => value + 1);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Document request failed."); }
    finally { setBusy(false); }
  }

  async function primary(document: DocumentRecord) {
    setBusy(true); setError(null);
    try {
      await read(await fetch(`/api/documents/${document.id}/primary`, { method: "PUT" }));
      setRevision(value => value + 1);
      setNotice("Primary manual updated.");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not select manual."); }
    finally { setBusy(false); }
  }

  async function download(document: DocumentRecord) {
    setBusy(true); setError(null);
    try {
      const { url } = await read(await fetch(`/api/attachments/${document.attachment_id}/access?download=true`));
      const anchor = window.document.createElement("a");
      anchor.href = url; anchor.rel = "noreferrer"; anchor.referrerPolicy = "no-referrer";
      window.document.body.append(anchor); anchor.click(); anchor.remove();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not open file."); }
    finally { setBusy(false); }
  }

  const selectable = files.filter(file => file.status === "uploaded" && file.mime_type === "application/pdf"
    && !documents.some(document => document.attachment_id === file.id));
  return (
    <section className="glass-card document-library" aria-label="Manuals and supporting documents">
      <h3>Manuals and supporting documents</h3>
      <p>Register an uploaded PDF, then confirm which machine and document type it describes.</p>
      <button disabled={busy} onClick={() => { setError(null); setRevision(value => value + 1); }}>Refresh uploaded files and documents</button>
      {loading ? <p role="status">Loading document records…</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {notice ? <p role="status">{notice}</p> : null}
      <form key={editing?.id ?? "new"} onSubmit={save} className="document-metadata-form">
        <h4>{editing ? "Review and confirm metadata" : "Register a document"}</h4>
        {!editing ? <>
          <label>Uploaded PDF<select name="attachment_id" required disabled={busy}>
            <option value="">Choose a PDF</option>
            {selectable.map(file => <option key={file.id} value={file.id}>{file.file_name}</option>)}
          </select></label>
          <label>Edition<select name="supersedes" disabled={busy}>
            <option value="">New document</option>
            {documents.filter(document => !documents.some(other => other.version_group_id === document.version_group_id && other.revision > document.revision)).map(document => (
              <option key={document.id} value={document.id}>New edition of {document.make} {document.model} · revision {document.revision}</option>
            ))}
          </select></label>
        </> : null}
        <label>Document type<select name="document_type" defaultValue={editing?.document_type ?? "manufacturer_manual"} disabled={busy}>
          <option value="manufacturer_manual">Manufacturer manual</option>
          <option value="supporting_document">Supporting document</option>
        </select></label>
        <label>Make<input name="make" defaultValue={editing?.make ?? bike.make} maxLength={100} required disabled={busy} /></label>
        <label>Model<input name="model" defaultValue={editing?.model ?? bike.model} maxLength={100} required disabled={busy} /></label>
        <label>Model year<input name="year" type="number" min={1885} max={2100} defaultValue={editing?.year ?? bike.year} required disabled={busy} /></label>
        <p>These starting values come from your bike profile. Check them against the document.</p>
        <button type="submit" disabled={busy || (!editing && selectable.length === 0)}>
          {busy ? "Saving…" : editing ? "Confirm document metadata" : "Register document"}
        </button>
        {editing ? <button type="button" disabled={busy} onClick={() => setEditing(null)}>Finish later</button> : null}
      </form>
      {!loading && documents.length === 0 ? <p>No document records yet.</p> : null}
      <ul className="document-files">
        {documents.map(document => <li key={document.id}>
          <strong>{document.year} {document.make} {document.model}</strong>
          <p>{document.document_type === "manufacturer_manual" ? "Manufacturer manual" : "Supporting document"} · revision {document.revision} · {document.status.replaceAll("_", " ")}{document.is_primary ? " · Primary manual" : ""}</p>
          <p>{files.find(file => file.id === document.attachment_id)?.file_name ?? "Uploaded PDF"}</p>
          <button disabled={busy} onClick={() => void download(document)}>Download PDF</button>
          {!document.confirmed_at && document.status === "awaiting_confirmation" ? <button disabled={busy} onClick={() => setEditing(document)}>Review metadata</button> : null}
          {document.confirmed_at && document.document_type === "manufacturer_manual" && !document.is_primary ? <button disabled={busy} onClick={() => void primary(document)}>Use as primary manual</button> : null}
          {document.confirmed_at ? <><DocumentIngestion documentId={document.id} /><DocumentIndex documentId={document.id} /></> : null}
        </li>)}
      </ul>
    </section>
  );
}
