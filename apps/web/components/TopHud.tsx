import { ActiveBikeSelector } from "@/components/ActiveBikeSelector";
import { BrandMark } from "@/components/BrandMark";
import { ProfileControl } from "@/components/ProfileControl";

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
      <ActiveBikeSelector />
      <div className="top-actions">
        <button type="button" className="bell" aria-label="Notifications">
          ●<i />
        </button>
        <ProfileControl />
      </div>
    </header>
  );
}
