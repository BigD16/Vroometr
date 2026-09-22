"use client";

export type AssistantCitation = {
  kind: string;
  label: string;
  document_id?: string | null;
  attachment_id?: string | null;
  document_type?: string | null;
  section_title?: string | null;
  page_start?: number | null;
  page_end?: number | null;
  is_primary?: boolean | null;
  file_name?: string | null;
  incomplete?: boolean;
};

/** Presentational Sources chips matching citation payloads from assistant_tools.citations. */
export function AssistantSources({
  citations,
  defaultOpen = false,
}: {
  citations: AssistantCitation[];
  defaultOpen?: boolean;
}) {
  if (citations.length === 0) return null;

  return (
    <details className="assistant-sources" open={defaultOpen || undefined}>
      <summary>
        Sources
        <span className="assistant-source-count">{citations.length}</span>
      </summary>
      <ul className="assistant-source-chips" aria-label="Cited sources">
        {citations.map((citation, index) => (
          <li key={`${citation.kind}-${citation.label}-${index}`}>
            <span
              className={[
                "assistant-source-chip",
                citation.kind === "manual" ? "is-manual" : null,
                citation.incomplete ? "is-incomplete" : null,
              ]
                .filter(Boolean)
                .join(" ")}
              title={citation.section_title ?? citation.label}
            >
              <small>{chipKind(citation)}</small>
              <b>{citation.label}</b>
              {citation.incomplete ? <em>partial</em> : null}
            </span>
          </li>
        ))}
      </ul>
    </details>
  );
}

function chipKind(citation: AssistantCitation): string {
  if (citation.kind === "manual") {
    return citation.is_primary ? "Primary manual" : "Manual";
  }
  if (citation.kind === "web") return "Web";
  if (citation.kind === "maintenance") return "Maintenance";
  if (citation.kind === "modification") return "Modification";
  return citation.kind.replace(/_/g, " ");
}
