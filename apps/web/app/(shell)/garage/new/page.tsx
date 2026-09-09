import { BikeForm } from "@/components/BikeForm";
import { WorkspacePage } from "@/components/WorkspacePage";

export default function NewBikePage() {
  return (
    <WorkspacePage
      kicker="GARAGE / NEW"
      title="Add a bike"
      description="Create the durable machine profile Vroometr will use everywhere."
      wide
    >
      <BikeForm />
    </WorkspacePage>
  );
}
