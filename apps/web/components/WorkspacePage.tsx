import type { ReactNode } from "react";

export function WorkspacePage({
  kicker,
  title,
  description,
  children,
}: {
  kicker: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <section className="workspace">
      <div className="workspace-title">
        <small>{kicker}</small>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <div className="workspace-body">
        {children ?? (
          <article className="glass-card">
            <p>Placeholder — live data lands in a later phase.</p>
          </article>
        )}
      </div>
    </section>
  );
}
