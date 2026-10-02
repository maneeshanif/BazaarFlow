"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { Bell, LogOut, Search, UserCircle } from "lucide-react";
import { NavIcon } from "@/components/app/icons";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { navFor, tabsFor, type NavGroup, type Role } from "@/lib/navigation";
import { useAuth } from "@/lib/auth/AuthProvider";
import { cn } from "@/lib/utils";

type Props = {
  role: Role;
  platformAdmin?: boolean;
  tenantName: string;
  userName?: string;
  /** href of the current page, to mark it with aria-current */
  activeHref?: string;
  children: ReactNode;
};

const focusRing = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus";

function NavList({ groups, activeHref, onNavigate }: { groups: NavGroup[]; activeHref?: string; onNavigate?: () => void }) {
  return (
    <>
      {groups.map((group) => (
        <div key={group.label} className="mb-3">
          <p className="px-3 pb-1 text-ui-2xs font-medium uppercase tracking-wide text-fg-subtle">{group.label}</p>
          <ul>
            {group.items.map((item) => {
              const base = "flex h-control-md items-center gap-2 rounded-md px-3 text-ui-base";
              if (!item.href) {
                return (
                  <li key={item.label}>
                    <span aria-disabled="true" title="Coming soon" className={cn(base, "cursor-not-allowed text-fg-subtle")}>
                      <NavIcon name={item.icon} />
                      <span className="truncate">{item.label}</span>
                      <span className="ml-auto text-ui-2xs">Soon</span>
                    </span>
                  </li>
                );
              }
              const active = item.href === activeHref;
              return (
                <li key={item.label}>
                  <Link
                    href={item.href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      base,
                      focusRing,
                      active ? "bg-action-subtle font-medium text-action" : "text-fg-muted hover:bg-surface-hover hover:text-fg",
                    )}
                  >
                    <NavIcon name={item.icon} />
                    <span className="truncate">{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </>
  );
}

/**
 * The application shell (PRD §4, ui-rules.md "Layout"): persistent sidebar on desktop, drawer on tablet and phone,
 * topbar with the shop switcher / search / notifications / user menu, and a five-item tab bar on phones.
 * Navigation is filtered by role: unauthorized modules are hidden, not disabled.
 */
export function AppShell({ role, platformAdmin = false, tenantName, userName, activeHref, children }: Props) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const groups = navFor(role, { platformAdmin });
  const { logout } = useAuth();

  return (
    <div className="min-h-screen bg-canvas text-fg">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded-md focus:bg-action focus:px-3 focus:py-2 focus:text-fg-inverse"
      >
        Skip to content
      </a>

      <aside
        data-testid="sidebar"
        className="fixed inset-y-0 left-0 z-30 hidden w-sidebar flex-col border-r border-border bg-surface lg:flex"
      >
        <div className="flex h-topbar items-center border-b border-border px-4">
          <span className="truncate text-ui-md font-semibold text-fg">BazaarFlow</span>
        </div>
        <nav aria-label="Main navigation" className="flex-1 overflow-y-auto p-2">
          <NavList groups={groups} activeHref={activeHref} />
        </nav>
      </aside>

      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent side="left" className="w-sidebar max-w-full overflow-y-auto bg-surface p-2">
          <SheetTitle className="px-3 py-2 text-ui-md font-semibold text-fg">BazaarFlow</SheetTitle>
          <SheetDescription className="sr-only">Navigation</SheetDescription>
          <nav aria-label="Drawer navigation">
            <NavList groups={groups} activeHref={activeHref} onNavigate={() => setDrawerOpen(false)} />
          </nav>
        </SheetContent>
      </Sheet>

      <div className="flex min-h-screen min-w-0 flex-col lg:pl-sidebar">
        <header className="sticky top-0 z-20 flex h-topbar items-center gap-2 border-b border-border bg-surface px-4">
          <button
            type="button"
            aria-label="Open navigation"
            onClick={() => setDrawerOpen(true)}
            className={cn("inline-flex h-control-md w-control-md items-center justify-center rounded-md text-fg-muted hover:bg-surface-hover lg:hidden", focusRing)}
          >
            <NavIcon name="menu" className="h-5 w-5" />
          </button>
          <span className="truncate text-ui-base font-medium text-fg">{tenantName}</span>
          <div className="ml-auto flex items-center gap-1">
            <button type="button" aria-label="Search" className={cn("inline-flex h-control-md w-control-md items-center justify-center rounded-md text-fg-muted hover:bg-surface-hover", focusRing)}>
              <Search aria-hidden className="h-4 w-4" />
            </button>
            <button type="button" aria-label="Notifications" className={cn("inline-flex h-control-md w-control-md items-center justify-center rounded-md text-fg-muted hover:bg-surface-hover", focusRing)}>
              <Bell aria-hidden className="h-4 w-4" />
            </button>
            <button type="button" aria-label={`User menu${userName ? `: ${userName}` : ""}`} className={cn("inline-flex h-control-md w-control-md items-center justify-center rounded-md text-fg-muted hover:bg-surface-hover", focusRing)}>
              <UserCircle aria-hidden className="h-5 w-5" />
            </button>
            <button
              type="button"
              aria-label="Sign out"
              onClick={() => void logout()}
              className={cn(
                "inline-flex h-control-md w-control-md items-center justify-center rounded-md text-fg-muted hover:bg-surface-hover",
                focusRing,
              )}
            >
              <LogOut aria-hidden className="h-4 w-4" />
            </button>
          </div>
        </header>

        <main id="main" tabIndex={-1} className="min-w-0 flex-1 p-4 pb-20 md:p-6 lg:pb-6">
          {children}
        </main>
      </div>

      <nav
        aria-label="Primary tabs"
        className="fixed inset-x-0 bottom-0 z-30 flex h-tabbar border-t border-border bg-surface lg:hidden"
      >
        {tabsFor(role).map((tab) => {
          const content = (
            <>
              <NavIcon name={tab.icon} className="h-5 w-5" />
              <span className="text-ui-2xs">{tab.label}</span>
            </>
          );
          const cls = cn(
            "flex flex-1 flex-col items-center justify-center gap-0.5 text-fg-muted",
            focusRing,
            tab.href && tab.href === activeHref && "text-action",
          );
          return tab.href ? (
            <Link key={tab.label} href={tab.href} aria-current={tab.href === activeHref ? "page" : undefined} className={cls}>
              {content}
            </Link>
          ) : (
            <button key={tab.label} type="button" onClick={() => setDrawerOpen(true)} className={cls}>
              {content}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
