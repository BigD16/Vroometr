export type FileProcessing = {
  state: "not_started" | "queued" | "running" | "completed" | "failed";
  scan_status: "not_scanned" | "clean" | "infected" | "error";
  error_code: string | null;
  retry_after: string | null;
};

const STATE_LABELS = {
  not_started: "Checks not started",
  queued: "Checks queued",
  running: "Checks running",
  completed: "Checks finished",
  failed: "Checks failed",
};
const SCAN_LABELS = {
  not_scanned: "Not scanned",
  clean: "Scan passed",
  infected: "Infected — file access blocked",
  error: "Scan unavailable",
};
const ERROR_MESSAGES: Record<string, string> = {
  queue_unavailable: "Could not start background checks. Try again when the service is available.",
  scanner_failed: "The scanner could not finish. You can retry these checks.",
  scan_failed: "Checks did not finish. You can retry them.",
};

export function ProcessingStatus({ processing }: { processing: FileProcessing }) {
  return (
    <div role="status" aria-live="polite">
      <p>{STATE_LABELS[processing.state]} · {SCAN_LABELS[processing.scan_status]}</p>
      {processing.state === "completed" && processing.scan_status === "not_scanned" ? (
        <p>Malware scanning is not configured yet. This file has not been scanned.</p>
      ) : null}
      {processing.error_code ? <p>{ERROR_MESSAGES[processing.error_code] ?? "Checks failed. Try again."}</p> : null}
      {processing.retry_after ? (
        <p>If checks stall, you can retry after {new Date(processing.retry_after).toLocaleString()}.</p>
      ) : null}
    </div>
  );
}
