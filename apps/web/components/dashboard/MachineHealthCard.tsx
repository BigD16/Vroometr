import { mockMachine } from "@/lib/mock-machine";

export function MachineHealthCard() {
  return (
    <article className="glass-card health">
      <header>
        <span>MACHINE HEALTH</span>
        <b>{mockMachine.healthPercent}%</b>
      </header>
      <div className="meter">
        <i style={{ width: `${mockMachine.healthPercent}%` }} />
      </div>
      <footer>
        <strong>{mockMachine.healthLabel}</strong>
        <span>{mockMachine.healthNote}</span>
      </footer>
    </article>
  );
}
