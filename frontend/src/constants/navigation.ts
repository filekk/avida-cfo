import type { IconName } from "@/components/ui/icons";

export interface NavItem {
  /** Route name (see router/index.ts). */
  to: string;
  label: string;
  icon: IconName;
  /** Show the number of pending decisions next to the label. */
  badge?: "pendingActions" | "findings";
}

export const NAV_ITEMS: NavItem[] = [
  { to: "dashboard", label: "Overview", icon: "dashboard" },
  { to: "decisions", label: "Action center", icon: "decisions", badge: "pendingActions" },
  { to: "contracts", label: "Contracts", icon: "document" },
  { to: "history", label: "History", icon: "history" },
];
