import { describe, expect, it } from "vitest";
import { navFor, tabsFor, type Role } from "@/lib/navigation";

const labels = (role: Role, platformAdmin = false) =>
  navFor(role, { platformAdmin }).flatMap((g) => g.items.map((i) => i.label));
const groups = (role: Role, platformAdmin = false) => navFor(role, { platformAdmin }).map((g) => g.label);

describe("navigation per role (PRD §4)", () => {
  it("shows the owner every tenant module", () => {
    expect(groups("owner")).toEqual(
      expect.arrayContaining(["Overview", "Inbox", "Sales", "Inventory", "Finance", "Marketing", "Voice", "Automations", "Settings"]),
    );
  });
  it("hides Finance, Marketing, Voice, Automations and Settings from staff, never merely disabling them", () => {
    const g = groups("staff");
    for (const hidden of ["Finance", "Marketing", "Voice", "Automations", "Settings"]) expect(g).not.toContain(hidden);
    expect(g).toEqual(expect.arrayContaining(["Overview", "Inbox", "Sales", "Inventory"]));
  });
  it("lets staff record sales and view stock but not manage vendors or customers' credit", () => {
    const l = labels("staff");
    expect(l).toEqual(expect.arrayContaining(["Home", "New sale", "Orders", "Products"]));
    expect(l).not.toContain("Vendors");
    expect(l).not.toContain("Approvals");
  });
  it("lets managers work but not change integrations, team or shop settings", () => {
    const l = labels("manager");
    expect(l).toEqual(expect.arrayContaining(["Approvals", "Vendors", "Studio"]));
    for (const hidden of ["Integrations", "Team", "Shop profile"]) expect(l).not.toContain(hidden);
  });
  it("gives only platform admins the operator group", () => {
    expect(groups("owner")).not.toContain("Platform");
    expect(groups("owner", true)).toContain("Platform");
  });
  it("marks pages that are not built yet instead of linking to a 404", () => {
    const items = navFor("owner").flatMap((g) => g.items);
    expect(items.some((i) => i.href)).toBe(true);
    expect(items.filter((i) => !i.href).every((i) => i.soon === true)).toBe(true);
  });
});

describe("phone tab bar follows the role (review of task 07)", () => {
  const hrefs = (role: Role) => new Set(navFor(role).flatMap((g) => g.items.map((i) => i.href).filter(Boolean)));

  it.each(["owner", "manager", "staff"] as const)("%s gets five tabs and every linked page is one the sidebar shows them", (role) => {
    const tabs = tabsFor(role);
    expect(tabs).toHaveLength(5);
    for (const tab of tabs.filter((t) => t.href)) expect(hrefs(role)).toContain(tab.href);
  });
  it("gives staff Orders instead of the manager-only support Inbox", () => {
    expect(tabsFor("staff").map((t) => t.label)).toContain("Orders");
    expect(tabsFor("staff").map((t) => t.label)).not.toContain("Inbox");
    expect(tabsFor("manager").map((t) => t.label)).toContain("Inbox");
  });
});
