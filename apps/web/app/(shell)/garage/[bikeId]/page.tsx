import { BikeDetails } from "@/components/BikeDetails";
import { WorkspacePage } from "@/components/WorkspacePage";
import { loadBike } from "@/lib/bike-server";

export default async function BikePage({
  params,
}: {
  params: Promise<{ bikeId: string }>;
}) {
  const { bikeId } = await params;
  const bike = await loadBike(bikeId);

  return (
    <WorkspacePage
      kicker="GARAGE / MACHINE"
      title={bike.nickname}
      description={`${bike.year} ${bike.make} ${bike.model}`}
      wide
    >
      <BikeDetails bike={bike} />
    </WorkspacePage>
  );
}
