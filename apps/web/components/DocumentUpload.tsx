"use client";

import { useState, type FormEvent } from "react";

import { readApiError } from "@/lib/api-errors";

type UploadPhase = "idle" | "authorizing" | "uploading" | "verifying" | "complete" | "error";

type PresignedUpload = {
  attachment_id: string;
  method: "POST";
  url: string;
  fields: Record<string, string>;
  expires_in: number;
};

type CompletedUpload = {
  attachment_id: string;
  file_name: string;
  file_size: number;
  status: "uploaded";
};

const PHASE_LABELS: Record<UploadPhase, string> = {
  idle: "Upload file",
  authorizing: "Authorizing…",
  uploading: "Uploading…",
  verifying: "Verifying…",
  complete: "Upload another",
  error: "Try again",
};

function formattedSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentUpload() {
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [completed, setCompleted] = useState<CompletedUpload | null>(null);
  const [pendingAttachmentId, setPendingAttachmentId] = useState<string | null>(null);
  const busy = phase === "authorizing" || phase === "uploading" || phase === "verifying";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setCompleted(null);
    setError(null);

    if (pendingAttachmentId) {
      await verifyUpload(pendingAttachmentId, form);
      return;
    }

    const input = form.elements.namedItem("file");
    if (!(input instanceof HTMLInputElement) || !input.files?.[0]) {
      setError("Choose a file before uploading.");
      setPhase("error");
      return;
    }

    const file = input.files[0];
    setPhase("authorizing");

    try {
      const presignResponse = await fetch("/api/uploads/presign", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          file_name: file.name,
          mime_type: file.type,
          file_size: file.size,
          purpose: "document",
        }),
      });
      if (!presignResponse.ok) {
        throw new Error(await readApiError(presignResponse, "Could not authorize this upload."));
      }
      const grant = (await presignResponse.json()) as PresignedUpload;

      setPhase("uploading");
      const uploadBody = new FormData();
      Object.entries(grant.fields).forEach(([name, value]) => uploadBody.append(name, value));
      uploadBody.append("file", file);
      const uploadResponse = await fetch(grant.url, {
        method: grant.method,
        body: uploadBody,
      });
      if (!uploadResponse.ok) {
        throw new Error("The file could not be uploaded to private storage.");
      }

      setPendingAttachmentId(grant.attachment_id);
      await verifyUpload(grant.attachment_id, form);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Upload failed.");
      setPhase("error");
    }
  }

  async function verifyUpload(attachmentId: string, form: HTMLFormElement) {
    setPhase("verifying");
    try {
      const completeResponse = await fetch(
        `/api/uploads/${encodeURIComponent(attachmentId)}/complete`,
        { method: "POST" },
      );
      if (!completeResponse.ok) {
        throw new Error(await readApiError(completeResponse, "Could not verify the upload."));
      }

      setCompleted((await completeResponse.json()) as CompletedUpload);
      setPendingAttachmentId(null);
      setPhase("complete");
      form.reset();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not verify the upload.");
      setPhase("error");
    }
  }

  return (
    <article className="glass-card document-upload">
      <header className="document-upload-header">
        <div>
          <small>DIRECT TO PRIVATE STORAGE</small>
          <h3>Add a document</h3>
          <p>PDF manuals up to 100 MB, or JPEG, PNG, and WebP images up to 15 MB.</p>
        </div>
        <span aria-hidden="true">↥</span>
      </header>

      <form onSubmit={submit}>
        <label className="document-file-picker">
          <span>Choose file</span>
          <input
            name="file"
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/jpeg,image/png,image/webp"
            disabled={busy || pendingAttachmentId !== null}
            required
          />
        </label>

        <ol className="document-upload-steps" aria-label="Upload steps">
          <li className={phase !== "idle" && phase !== "error" ? "is-active" : ""}>
            <b>01</b>
            <span>Authorize</span>
          </li>
          <li className={phase === "uploading" || phase === "verifying" ? "is-active" : ""}>
            <b>02</b>
            <span>Transfer</span>
          </li>
          <li className={phase === "verifying" || phase === "complete" ? "is-active" : ""}>
            <b>03</b>
            <span>Verify</span>
          </li>
        </ol>

        <button
          className="garage-action garage-action-primary document-upload-action"
          type="submit"
          disabled={busy}
        >
          {pendingAttachmentId && phase === "error"
            ? "Retry verification"
            : PHASE_LABELS[phase]}
        </button>
      </form>

      {error ? (
        <p className="garage-inline-error" role="alert">
          {error}
        </p>
      ) : null}
      {completed ? (
        <div className="document-upload-success" role="status">
          <span aria-hidden="true">✓</span>
          <div>
            <strong>{completed.file_name}</strong>
            <small>
              {formattedSize(completed.file_size)} · Private upload verified
            </small>
          </div>
        </div>
      ) : null}

      <footer>
        The browser sends the file straight to object storage. Vroometr only authorizes and
        verifies the upload.
      </footer>
    </article>
  );
}
