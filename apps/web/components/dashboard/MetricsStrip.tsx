import { mockMachine } from "@/lib/mock-machine";

export function MetricsStrip() {
  return (
    <section className="metrics">
      <div>
        <small>ENGINE HOURS</small>
        <b>{mockMachine.engineHours}</b>
      </div>
      <div>
        <small>SINCE SERVICE</small>
        <b>
          {mockMachine.hoursSinceService} <em>HRS</em>
        </b>
      </div>
      <div>
        <small>MANUAL</small>
        <b className="green">● READY</b>
      </div>
      <div>
        <small>LAST RIDE</small>
        <b>{mockMachine.lastRide}</b>
      </div>
    </section>
  );
}
