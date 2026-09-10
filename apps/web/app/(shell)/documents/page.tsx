import { DocumentUpload } from "@/components/DocumentUpload";
import { WorkspacePage } from "@/components/WorkspacePage";

export default function DocumentsPage() {
  return (
    <WorkspacePage
      kicker="YOUR RECORDS"
      title="Documents"
      description="Upload manuals and reference files directly to private storage."
      wide
    >
      <DocumentUpload />
    </WorkspacePage>
  );
}
