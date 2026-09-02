import { BrandMark } from "@/components/BrandMark";

export default function AssistantPage() {
  return (
    <section className="assistant-screen">
      <div className="assistant-heading">
        <BrandMark />
        <div>
          <small>VROOMETR ASSISTANT</small>
          <h2>Diagnose with your machine’s context</h2>
        </div>
      </div>
      <div className="chat">
        <p className="placeholder-copy">
          Conversations are not wired yet. This screen is the visual shell.
        </p>
      </div>
      <div className="composer">
        <button type="button" aria-label="Add">
          ＋
        </button>
        <span>Message Vroometr about your bike…</span>
        <button type="button" className="send" aria-label="Send">
          ↑
        </button>
      </div>
      <p className="disclaimer">Verify critical specifications in your manual before servicing.</p>
    </section>
  );
}
