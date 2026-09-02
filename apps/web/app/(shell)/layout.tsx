import type { ReactNode } from "react";

import { GarageShell } from "@/components/GarageShell";

export default function ShellLayout({ children }: { children: ReactNode }) {
  return <GarageShell>{children}</GarageShell>;
}
