import { mockUpNext } from "@/lib/mock-machine";

export function UpNextCard() {
  const [priority, ...rest] = mockUpNext;

  return (
    <article className="glass-card">
      <header>
        <span>UP NEXT</span>
        <button type="button">VIEW ALL →</button>
      </header>
      {priority ? (
        <div className="priority">
          <i />
          <div>
            <b>{priority.title}</b>
            <span>{priority.detail}</span>
          </div>
        </div>
      ) : null}
      {rest.map((item) => (
        <div className="service-line" key={item.title}>
          <div>
            <b>{item.title}</b>
            <span>{item.detail}</span>
          </div>
          <strong>{item.due}</strong>
        </div>
      ))}
    </article>
  );
}
