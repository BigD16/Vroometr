import { DocumentsWorkspace } from "@/components/DocumentsWorkspace";
import { WorkspacePage } from "@/components/WorkspacePage";

export default function DocumentsPage() {
  return (
    <WorkspacePage
      kicker="YOUR RECORDS"
      title="Documents"
      description="Manage manuals and reference files for your machine."
      wide
    >
      <DocumentsWorkspace />
    </WorkspacePage>
  );
}
