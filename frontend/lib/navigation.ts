/**
 * Main navigation (PRD §4). Which items a role sees is decided here; unauthorized items are hidden, never merely
 * disabled. The API still enforces every permission, hiding is a convenience.
 *
 * `href` points at a page that exists today. An item without one is a planned page and is shown as "Soon" instead of
 * linking to a 404 (it appears in the PRD, and the phase that builds it is noted).
 */

export type Role = "owner" | "manager" | "staff";

export type NavItem = {
  label: string;
  icon: string;
  roles: Role[];
  href?: string;
  /** true when the page is planned but not built yet */
  soon?: true;
};

export type NavGroup = { label: string; items: NavItem[] };

const ALL: Role[] = ["owner", "manager", "staff"];
const MANAGER_UP: Role[] = ["owner", "manager"];
const OWNER: Role[] = ["owner"];

export const NAV: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { label: "Home", icon: "home", roles: ALL, href: "/dashboard" },
      { label: "Agent activity", icon: "activity", roles: MANAGER_UP, href: "/agent-activity" },
      { label: "Approvals", icon: "check-circle", roles: MANAGER_UP, href: "/approvals" },
    ],
  },
  {
    label: "Inbox",
    items: [
      { label: "Conversations", icon: "message-square", roles: ALL, soon: true },
      { label: "Support calls", icon: "phone", roles: MANAGER_UP, href: "/dashboard/support" },
    ],
  },
  {
    label: "Sales",
    items: [
      { label: "Sales chat", icon: "bot", roles: ALL, href: "/sales/chat" },
      { label: "New sale", icon: "plus-circle", roles: ALL, href: "/sales/new" },
      { label: "Orders", icon: "receipt", roles: ALL, href: "/orders" },
      { label: "Customers", icon: "users", roles: MANAGER_UP, href: "/customers" },
    ],
  },
  {
    label: "Inventory",
    items: [
      { label: "Products", icon: "package", roles: ALL, href: "/inventory" },
      { label: "Stock movements", icon: "arrow-left-right", roles: MANAGER_UP, soon: true },
      { label: "Vendors", icon: "truck", roles: MANAGER_UP, soon: true },
    ],
  },
  {
    label: "Finance",
    items: [{ label: "Finance overview", icon: "wallet", roles: MANAGER_UP, soon: true }],
  },
  {
    label: "Marketing",
    items: [
      { label: "Studio", icon: "megaphone", roles: MANAGER_UP, href: "/dashboard/marketing" },
      { label: "Schedule", icon: "calendar", roles: MANAGER_UP, href: "/dashboard/marketing/schedule" },
      { label: "Insights", icon: "bar-chart", roles: MANAGER_UP, href: "/dashboard/marketing/insights" },
    ],
  },
  {
    label: "Voice",
    items: [{ label: "Call log", icon: "headphones", roles: MANAGER_UP, soon: true }],
  },
  {
    label: "Automations",
    items: [{ label: "Recipes", icon: "workflow", roles: MANAGER_UP, soon: true }],
  },
  {
    label: "Settings",
    items: [
      { label: "Shop profile", icon: "store", roles: OWNER, href: "/dashboard/settings" },
      { label: "Team", icon: "user-cog", roles: OWNER, href: "/team" },
      { label: "Integrations", icon: "plug", roles: OWNER, href: "/dashboard/marketing/credentials" },
    ],
  },
];

const PLATFORM: NavGroup = {
  label: "Platform",
  items: [
    { label: "Tenants", icon: "building", roles: ALL, soon: true },
    { label: "System logs", icon: "scroll-text", roles: ALL, href: "/logs" },
  ],
};

/** The groups and items a user with this role (and operator flag) may see. Empty groups are dropped. */
export function navFor(role: Role, opts: { platformAdmin?: boolean } = {}): NavGroup[] {
  const groups = NAV.map((g) => ({ ...g, items: g.items.filter((i) => i.roles.includes(role)) })).filter(
    (g) => g.items.length > 0,
  );
  return opts.platformAdmin ? [...groups, PLATFORM] : groups;
}

export type Tab = { label: string; icon: string; href?: string; menu?: true };

/**
 * The five destinations of the phone tab bar (PRD §4), chosen by role so it never offers a page the sidebar hides:
 * managers and owners get the support Inbox, staff get Orders instead.
 */
export function tabsFor(role: Role): Tab[] {
  const second: Tab =
    role === "staff"
      ? { label: "Orders", icon: "receipt", href: "/orders" }
      : { label: "Inbox", icon: "message-square", href: "/dashboard/support" };
  return [
    { label: "Home", icon: "home", href: "/dashboard" },
    second,
    { label: "Sales", icon: "bot", href: "/sales/chat" },
    { label: "Stock", icon: "package", href: "/inventory" },
    { label: "More", icon: "menu", menu: true },
  ];
}

/** The nav href that owns a pathname: the longest href the path starts with (so /inventory/abc marks Products). */
export function activeHrefFor(pathname: string): string | undefined {
  const hrefs = NAV.flatMap((g) => g.items.map((i) => i.href)).filter((h): h is string => Boolean(h));
  const owners = hrefs.filter((h) => pathname === h || pathname.startsWith(`${h}/`));
  return owners.sort((a, b) => b.length - a.length)[0];
}
