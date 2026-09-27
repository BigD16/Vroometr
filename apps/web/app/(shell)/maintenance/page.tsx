import { MaintenanceWorkspace } from "@/components/MaintenanceWorkspace";
import { WorkspacePage } from "@/components/WorkspacePage";

export default function MaintenancePage() {
  return (
    <WorkspacePage
      kicker="SERVICE BAY"
      title="Maintenance"
      description="Track every hour. Catch every service."
      wide
    >
      <MaintenanceWorkspace />
    </WorkspacePage>
  );
}
