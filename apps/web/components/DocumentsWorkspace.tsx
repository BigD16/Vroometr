"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { useActiveBike } from "@/components/ActiveBikeProvider";
import { DocumentRecords } from "@/components/DocumentRecords";
import { DocumentLibrary } from "@/components/DocumentLibrary";
import { DocumentSearch } from "@/components/DocumentSearch";

export function DocumentsWorkspace() {
  const { activeBike, state, error, reload } = useActiveBike();
  const [filesRevision, setFilesRevision] = useState(0);
  const onFilesChange = useCallback(() => setFilesRevision(value => value + 1), []);
  if (state === "loading") return <p role="status">Loading your bike…</p>;
  if (state === "error") return (
    <div role="alert"><p>{error}</p><button onClick={() => void reload()}>Retry</button></div>
  );
  if (!activeBike) return (
    <div className="glass-card document-library">
      <p>Add a bike to start organizing its documents.</p>
      <Link href="/garage">Go to Garage</Link>
      <DocumentLibrary key="account" bikeId={null} />
    </div>
  );
  return <div className="documents-workspace" key={activeBike.id}>
    <DocumentSearch key={`${activeBike.id}:${filesRevision}`} bikeId={activeBike.id} />
    <DocumentLibrary bikeId={activeBike.id} onFilesChange={onFilesChange} />
    <DocumentRecords bike={activeBike} filesRevision={filesRevision} />
  </div>;
}
