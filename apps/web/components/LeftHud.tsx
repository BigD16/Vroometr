"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { MAIN_NAV, SETTINGS_NAV, isActivePath } from "@/lib/nav";

export function LeftHud() {
  const pathname = usePathname();

  return (
    <aside className="left-hud">
      <nav aria-label="Main">
        {MAIN_NAV.map((item) => {
          const active = isActivePath(pathname, item.href);
          const label = item.comingSoon ? "Suspension — Coming Soon" : item.label;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={active ? "active" : undefined}
              aria-current={active ? "page" : undefined}
              aria-label={label}
              title={label}
            >
              <span>{item.icon}</span>
              <small>{item.label}</small>
            </Link>
          );
        })}
      </nav>
      <Link
        href={SETTINGS_NAV.href}
        className={`settings${isActivePath(pathname, SETTINGS_NAV.href) ? " active" : ""}`}
        aria-current={isActivePath(pathname, SETTINGS_NAV.href) ? "page" : undefined}
        aria-label={SETTINGS_NAV.label}
      >
        {SETTINGS_NAV.icon}
      </Link>
    </aside>
  );
}
