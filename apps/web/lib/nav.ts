export type NavItem = {
  href: string;
  label: string;
  icon: string;
  scene: string;
  comingSoon?: boolean;
};

/** Locked V1 nav. Settings sits at the bottom of the rail. */
export const MAIN_NAV: NavItem[] = [
  { href: "/", label: "Dashboard", icon: "⌂", scene: "dashboard" },
  { href: "/garage", label: "Garage", icon: "▣", scene: "dashboard" },
  { href: "/assistant", label: "Assistant", icon: "✦", scene: "assistant" },
  { href: "/maintenance", label: "Maint.", icon: "◇", scene: "maintenance" },
  { href: "/rides", label: "Rides", icon: "⌁", scene: "rides" },
  { href: "/documents", label: "Docs", icon: "▤", scene: "documents" },
  { href: "/modifications", label: "Mods", icon: "＋", scene: "modifications" },
  { href: "/issues", label: "Issues", icon: "!", scene: "dashboard" },
  {
    href: "/suspension",
    label: "Soon",
    icon: "≈",
    scene: "dashboard",
    comingSoon: true,
  },
];

export const SETTINGS_NAV: NavItem = {
  href: "/settings",
  label: "Settings",
  icon: "⚙",
  scene: "dashboard",
};

export function sceneForPath(pathname: string): string {
  const item = [...MAIN_NAV, SETTINGS_NAV].find((entry) =>
    entry.href === "/" ? pathname === "/" : pathname.startsWith(entry.href),
  );
  return item?.scene ?? "dashboard";
}

export function isActivePath(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname.startsWith(href);
}
