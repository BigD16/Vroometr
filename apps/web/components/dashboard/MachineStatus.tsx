import { mockMachine } from "@/lib/mock-machine";

export function MachineStatus() {
  return (
    <section className="scene-label">
      <small>{mockMachine.statusKicker}</small>
      <h2>
        {mockMachine.statusTitle} <i />
      </h2>
      <p>{mockMachine.statusDetail}</p>
    </section>
  );
}
