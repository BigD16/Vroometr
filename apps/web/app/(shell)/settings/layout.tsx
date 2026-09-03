import type { ReactNode } from "react";

import { SettingsSubnav } from "@/components/SettingsSubnav";
import { WorkspacePage } from "@/components/WorkspacePage";

export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <WorkspacePage
      kicker="ACCOUNT"
      title="Settings"
      description="Account, notifications, and data controls."
    >
      <div className="settings-stack">
        <SettingsSubnav />
        {children}
      </div>
    </WorkspacePage>
  );
}
