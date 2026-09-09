import { BikeForm } from "@/components/BikeForm";
import { WorkspacePage } from "@/components/WorkspacePage";
import { loadBike } from "@/lib/bike-server";

export default async function EditBikePage({
  params,
}: {
  params: Promise<{ bikeId: string }>;
}) {
  const { bikeId } = await params;
  const bike = await loadBike(bikeId);

  return (
    <WorkspacePage
      kicker="GARAGE / EDIT"
      title={`Edit ${bike.nickname}`}
      description="Update this machine's structured profile and Garage status."
      wide
    >
      <BikeForm bike={bike} />
    </WorkspacePage>
  );
}
