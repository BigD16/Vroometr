import { BrandMark } from "@/components/BrandMark";
import { AssistantWorkspace } from "@/components/AssistantWorkspace";

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
      <AssistantWorkspace />
      <p className="disclaimer">Verify critical specifications in your manual before servicing.</p>
    </section>
  );
}
