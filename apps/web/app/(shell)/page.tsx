import { MachineHealthCard } from "@/components/dashboard/MachineHealthCard";
import { MachineStatus } from "@/components/dashboard/MachineStatus";
import { MetricsStrip } from "@/components/dashboard/MetricsStrip";
import { PlannedRideCard } from "@/components/dashboard/PlannedRideCard";
import { UpNextCard } from "@/components/dashboard/UpNextCard";

export default function DashboardPage() {
  return (
    <>
      <MachineStatus />
      <aside className="panel-stack right-panel">
        <MachineHealthCard />
        <UpNextCard />
        <PlannedRideCard />
      </aside>
      <MetricsStrip />
    </>
  );
}
