import type { ReactNode } from "react";

export function WorkspacePage({
  kicker,
  title,
  description,
  children,
  wide = false,
}: {
  kicker: string;
  title: string;
  description: string;
  children?: ReactNode;
  wide?: boolean;
}) {
  return (
    <section className="workspace">
      <div className="workspace-title">
        <small>{kicker}</small>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <div className={`workspace-body${wide ? " workspace-body-wide" : ""}`}>
        {children ?? (
          <article className="glass-card">
            <p>Placeholder — live data lands in a later phase.</p>
          </article>
        )}
      </div>
    </section>
  );
}
