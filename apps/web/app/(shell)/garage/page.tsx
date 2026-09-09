import { GarageList } from "@/components/GarageList";
import { WorkspacePage } from "@/components/WorkspacePage";

export default function GaragePage() {
  return (
    <WorkspacePage
      kicker="YOUR MACHINES"
      title="Garage"
      description="Every bike you own, with one active machine across Vroometr."
      wide
    >
      <GarageList />
    </WorkspacePage>
  );
}
