"use client";

import { useCallback, useEffect, useState } from "react";
import { ProcessingStatus, type FileProcessing } from "@/components/ProcessingStatus";
import { DocumentUpload } from "@/components/DocumentUpload";
import { readApiError } from "@/lib/api-errors";

type FileRecord = {
  id: string; file_name: string; file_size: number; mime_type: string;
  processing: FileProcessing;
  status: string; link_ids: string[]; link_count: number; deletable_after: string;
};
type Usage = { used_bytes: number; limit_bytes: number };

function size(bytes: number) {
  return bytes >= 1024 ** 3 ? `${(bytes / 1024 ** 3).toFixed(2)} GB`
    : `${(bytes / 1024 ** 2).toFixed(2)} MB`;
}

async function checked(response: Response): Promise<Response> {
  if (!response.ok) throw new Error(await readApiError(response, "Could not complete this action."));
  return response;
}

export function DocumentLibrary({ bikeId, onFilesChange }: { bikeId: string | null; onFilesChange?: () => void }) {
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [showAll, setShowAll] = useState(bikeId === null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [preview, setPreview] = useState<{ id: string; url: string; name: string } | null>(null);
  const [deleteWaiting, setDeleteWaiting] = useState(false);
  const [deleting, setDeleting] = useState<FileRecord | null>(null);
  const refresh = useCallback(() => setRevision(value => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ include_all: "true" });
    if (bikeId) query.set("bike_id", bikeId);
    let poll: ReturnType<typeof setTimeout> | undefined;
    Promise.all([
      fetch(`/api/attachments?${query}`, { signal: controller.signal }).then(checked).then(r => r.json()),
      fetch("/api/storage", { signal: controller.signal }).then(checked).then(r => r.json()),
    ]).then(([records, storage]: [FileRecord[], Usage]) => {
      if (!controller.signal.aborted) {
        setFiles(records); setUsage(storage); setLoading(false);
        if (records.some(file => ["queued", "running"].includes(file.processing.state))) {
          poll = setTimeout(refresh, 3000);
        }
      }
    }).catch(caught => {
      if (!controller.signal.aborted) { setError(caught.message); setLoading(false); }
    });
    return () => { controller.abort(); if (poll) clearTimeout(poll); };
  }, [bikeId, revision, refresh]);

  async function action(operation: () => Promise<void>) {
    setBusy(true); setError(null);
    try { await operation(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Action failed."); }
    finally { setBusy(false); refresh(); onFilesChange?.(); }
  }

  async function access(file: FileRecord, download: boolean) {
    const response = await checked(await fetch(`/api/attachments/${file.id}/access?download=${download}`));
    const { url } = await response.json() as { url: string };
    if (download) {
      const anchor = document.createElement("a");
      anchor.href = url; anchor.rel = "noreferrer"; anchor.referrerPolicy = "no-referrer";
      document.body.append(anchor); anchor.click(); anchor.remove();
    } else setPreview({ id: file.id, url, name: file.file_name });
  }

  const safePreview = preview && files.some(file => file.id === preview.id && file.processing.scan_status !== "infected") ? preview : null;
  const visible = files.filter(file => showAll || file.link_ids.length > 0);
  return (
    <div className="documents-workspace">
      {bikeId ? <DocumentUpload bikeId={bikeId} onChange={() => { refresh(); onFilesChange?.(); }} /> : null}
      <section className="glass-card document-library" aria-label="Document library">
        <header>
          <h3>{showAll ? "Account files" : "This bike’s files"}</h3>
          {usage ? <p>{size(usage.used_bytes)} of {size(usage.limit_bytes)} used, including pending uploads.</p> : null}
          {bikeId ? <label><input type="checkbox" checked={showAll}
            onChange={e => setShowAll(e.target.checked)} /> Show all account files</label> : null}
        </header>
        {error ? <div role="alert"><p>{error}</p><button onClick={() => { setError(null); refresh(); }}>Refresh files</button></div> : null}
        {loading ? <p role="status">Loading documents…</p> : null}
        {!loading && !error && visible.length === 0 ? <p>No documents here yet. Upload a file or choose one from your account files.</p> : null}
        <ul className="document-files">
          {visible.map(file => (
            <li key={file.id}>
              <strong>{file.file_name}</strong>
              <p>{size(file.file_size)} · {file.status === "uploaded" ? "Uploaded" : "Pending verification"} · {file.link_count} link(s)</p>
              <ProcessingStatus processing={file.processing} />
              <div className="document-file-actions">
                {file.status === "uploaded" ? <button disabled={busy} onClick={() => void action(async () => {
                  await checked(await fetch(`/api/attachments/${file.id}/processing`, { method: "POST" }));
                })}>{file.processing.state === "not_started" ? "Run checks" : "Retry checks"}</button> : null}
                {file.status === "uploaded" ? <>
                  <button disabled={busy || file.processing.scan_status === "infected"} onClick={() => void action(() => access(file, false))}>View</button>
                  <button disabled={busy || file.processing.scan_status === "infected"} onClick={() => void action(() => access(file, true))}>Download</button>
                  {bikeId && file.link_ids.length === 0 ? <button disabled={busy} onClick={() => void action(async () => {
                    await checked(await fetch("/api/attachment-links", { method: "POST",
                      headers: { "content-type": "application/json" },
                      body: JSON.stringify({ attachment_id: file.id, entity_type: "bike", entity_id: bikeId }),
                    }));
                  })}>Add to this bike</button> : null}
                </> : <button disabled={busy} onClick={() => void action(async () => {
                  await checked(await fetch(`/api/uploads/${file.id}/complete`, { method: "POST" }));
                })}>Verify upload</button>}
                {file.link_ids.length > 0 ? <button disabled={busy} onClick={() => void action(async () => {
                  for (const linkId of file.link_ids) {
                    const response = await fetch(`/api/attachment-links/${linkId}`, { method: "DELETE" });
                    if (response.status !== 404) await checked(response);
                  }
                })}>Remove from this bike</button> : null}
                <button disabled={busy} onClick={() => { setDeleting(file); setDeleteWaiting(Date.now() < Date.parse(file.deletable_after)); }}>Delete file…</button>
              </div>
              {deleting?.id === file.id ? <div className="document-delete-confirm" role="group" aria-label="Confirm file deletion">
                <p>Delete “{file.file_name}” permanently from your account and every linked bike or record? All its links and document records will be removed. This cannot be undone.</p>
                {deleteWaiting ? <p>Permanent deletion is available after {new Date(file.deletable_after).toLocaleTimeString()}, when the upload grant expires.</p> : null}
                <button disabled={busy} onClick={() => void action(async () => {
                  const response = await fetch(`/api/attachments/${file.id}`, { method: "DELETE",
                    headers: { "content-type": "application/json" }, body: JSON.stringify({ confirmed: true }),
                  });
                  if (response.status !== 404) await checked(response);
                  setDeleting(null);
                })}>Permanently delete file</button>
                <button disabled={busy} onClick={() => setDeleting(null)}>Cancel</button>
              </div> : null}
            </li>
          ))}
        </ul>
        <p>Check each file’s scan status before opening it. “Not scanned” is not a clean verdict.</p>
      </section>
      {safePreview ? <section className="glass-card document-preview" aria-label={`Preview of ${safePreview.name}`}>
        <header><h3>{safePreview.name}</h3><button onClick={() => setPreview(null)}>Close preview</button></header>
        <p>Preview is isolated. If your browser cannot display this file, use Download.</p>
        <iframe title={safePreview.name} src={safePreview.url} sandbox="" referrerPolicy="no-referrer" />
      </section> : null}
    </div>
  );
}
