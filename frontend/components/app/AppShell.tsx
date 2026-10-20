"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { Bell, LogOut, Search, UserCircle } from "lucide-react";
import { LanguageSwitcher } from "@/components/app/LanguageSwitcher";
import { NavIcon } from "@/components/app/icons";
import { useT } from "@/lib/i18n/LocaleProvider";
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

const focusRing = "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus";
/** the sidebar, drawer and tab bar are forest green in both themes, so their focus ring is lime */
const navFocus = "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-lime";

function NavList({ groups, activeHref, onNavigate }: { groups: NavGroup[]; activeHref?: string; onNavigate?: () => void }) {
  const t = useT();
  return (
    <>
      {groups.map((group) => (
        <div key={group.label} className="mb-3">
          <p className="px-4 pb-1 font-display text-ui-sm uppercase tracking-wide text-lime">{t(group.label)}</p>
          <ul>
            {group.items.map((item) => {
              const base = "flex h-control-md items-center gap-3 rounded-pill px-4 text-ui-base font-bold";
              if (!item.href) {
                return (
                  <li key={item.label}>
                    <span aria-disabled="true" title="Coming soon" className={cn(base, "cursor-not-allowed text-cream/70")}>
                      <NavIcon name={item.icon} />
                      <span className="truncate">{t(item.label)}</span>
                      <span className="ms-auto text-ui-2xs">{t("Soon")}</span>
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
                      navFocus,
                      active ? "bg-lime text-forest-ink" : "text-cream hover:bg-forest-deep",
                    )}
                  >
                    <NavIcon name={item.icon} />
                    <span className="truncate">{t(item.label)}</span>
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
  const t = useT();

  return (
    <div className="min-h-screen bg-canvas text-fg">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:start-2 focus:top-2 focus:z-50 focus:rounded-md focus:bg-action focus:px-3 focus:py-2 focus:text-fg-inverse"
      >
        {t("Skip to content")}
      </a>

      <aside
        data-testid="sidebar"
        className="fixed inset-y-0 start-0 z-30 hidden w-sidebar flex-col bg-forest text-cream lg:flex"
      >
        <div className="flex h-topbar items-center border-b-2 border-dotted border-lime/50 px-5">
          <span className="truncate font-display text-ui-2xl uppercase tracking-wide text-lime">BazaarFlow</span>
        </div>
        <nav aria-label={t("Main navigation")} className="flex-1 overflow-y-auto p-3">
          <NavList groups={groups} activeHref={activeHref} />
        </nav>
      </aside>

      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent side="left" className="w-sidebar max-w-full overflow-y-auto border-0 bg-forest p-3 text-cream">
          <SheetTitle className="px-4 py-2 font-display text-ui-2xl uppercase text-lime">BazaarFlow</SheetTitle>
          <SheetDescription className="sr-only">Navigation</SheetDescription>
          <nav aria-label={t("Drawer navigation")}>
            <NavList groups={groups} activeHref={activeHref} onNavigate={() => setDrawerOpen(false)} />
          </nav>
        </SheetContent>
      </Sheet>

      <div className="flex min-h-screen min-w-0 flex-col lg:ps-sidebar">
        <header className="sticky top-0 z-20 flex h-topbar items-center gap-2 border-b-2 border-line-strong bg-surface px-4 md:px-6">
          <button
            type="button"
            aria-label={t("Open navigation")}
            onClick={() => setDrawerOpen(true)}
            className={cn("inline-flex h-control-md w-control-md items-center justify-center rounded-full text-fg hover:bg-lime hover:text-forest-ink lg:hidden", focusRing)}
          >
            <NavIcon name="menu" className="h-5 w-5" />
          </button>
          <span className="truncate font-display text-ui-xl uppercase tracking-wide text-fg">{tenantName}</span>
          <div className="ms-auto flex items-center gap-1">
            <LanguageSwitcher className="me-1" />
            <button type="button" aria-label={t("Search")} className={cn("inline-flex h-control-md w-control-md items-center justify-center rounded-full text-fg hover:bg-lime hover:text-forest-ink", focusRing)}>
              <Search aria-hidden className="h-4 w-4" />
            </button>
            <button type="button" aria-label={t("Notifications")} className={cn("inline-flex h-control-md w-control-md items-center justify-center rounded-full text-fg hover:bg-lime hover:text-forest-ink", focusRing)}>
              <Bell aria-hidden className="h-4 w-4" />
            </button>
            <button type="button" aria-label={`User menu${userName ? `: ${userName}` : ""}`} className={cn("inline-flex h-control-md w-control-md items-center justify-center rounded-full text-fg hover:bg-lime hover:text-forest-ink", focusRing)}>
              <UserCircle aria-hidden className="h-5 w-5" />
            </button>
            <button
              type="button"
              aria-label={t("Sign out")}
              onClick={() => void logout()}
              className={cn(
                "inline-flex h-control-md w-control-md items-center justify-center rounded-full text-fg hover:bg-lime hover:text-forest-ink",
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
        aria-label={t("Primary tabs")}
        className="fixed inset-x-0 bottom-0 z-30 flex h-tabbar bg-forest text-cream lg:hidden"
      >
        {tabsFor(role).map((tab) => {
          const content = (
            <>
              <NavIcon name={tab.icon} className="h-5 w-5" />
              <span className="text-ui-2xs">{t(tab.label)}</span>
            </>
          );
          const cls = cn(
            "flex flex-1 flex-col items-center justify-center gap-0.5 font-bold text-cream",
            navFocus,
            tab.href && tab.href === activeHref && "text-lime",
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
