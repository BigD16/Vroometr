import { BrandMark } from "@/components/BrandMark";
import { mockMachine, mockUser } from "@/lib/mock-machine";

export function TopHud() {
  return (
    <header className="top-hud">
      <div className="brand">
        <BrandMark />
        <div>
          <strong>VROOMETR</strong>
          <small>KNOW YOUR MACHINE.</small>
        </div>
      </div>
      <div className="machine-title">
        <span>
          <i /> ACTIVE MACHINE
        </span>
        <h1>{mockMachine.nickname}</h1>
        <p>{mockMachine.identityLine}</p>
      </div>
      <div className="top-actions">
        <button type="button" className="bell" aria-label="Notifications">
          ●<i />
        </button>
        <button type="button" className="profile">
          <span>{mockUser.initials}</span>
          <div>
            <b>{mockUser.displayName}</b>
            <small>{mockUser.planLabel}</small>
          </div>
          <em>⌄</em>
        </button>
      </div>
    </header>
  );
}
