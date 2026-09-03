"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const SECTIONS = [
  { href: "/settings", label: "Account" },
  { href: "/settings/notifications", label: "Notifications" },
  { href: "/settings/privacy", label: "Data & Privacy" },
] as const;

export function SettingsSubnav() {
  const pathname = usePathname();

  return (
    <nav className="settings-subnav" aria-label="Settings sections">
      {SECTIONS.map((section) => {
        const active =
          section.href === "/settings"
            ? pathname === "/settings"
            : pathname.startsWith(section.href);
        return (
          <Link
            key={section.href}
            href={section.href}
            className={active ? "active" : undefined}
            aria-current={active ? "page" : undefined}
          >
            {section.label}
          </Link>
        );
      })}
    </nav>
  );
}
