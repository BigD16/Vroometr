"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import { AssistantFab } from "@/components/AssistantFab";
import { LeftHud } from "@/components/LeftHud";
import { TopHud } from "@/components/TopHud";
import { sceneForPath } from "@/lib/nav";

export function GarageShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const scene = sceneForPath(pathname);
  const showFab = pathname !== "/assistant";

  return (
    <div className={`garage-app scene-${scene}`}>
      <div className="scene-image" />
      <div className="scene-shade" />
      <TopHud />
      <LeftHud />
      <div className="page-content">{children}</div>
      {showFab ? <AssistantFab /> : null}
    </div>
  );
}
