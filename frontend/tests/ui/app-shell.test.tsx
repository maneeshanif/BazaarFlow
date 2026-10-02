import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AppShell } from "@/components/app/AppShell";

describe("AppShell (PRD §4, §16)", () => {
  it("offers a skip link, a main landmark and a labelled main navigation", () => {
    render(
      <AppShell role="owner" tenantName="Ali Mart">
        <p>content</p>
      </AppShell>,
    );
    expect(screen.getByRole("link", { name: /skip to content/i })).toHaveAttribute("href", "#main");
    expect(screen.getByRole("main")).toHaveAttribute("id", "main");
    expect(screen.getByRole("navigation", { name: /main/i })).toBeInTheDocument();
  });

  it("shows the shop name and renders the page content", () => {
    render(
      <AppShell role="owner" tenantName="Ali Mart">
        <p>hello page</p>
      </AppShell>,
    );
    expect(screen.getAllByText("Ali Mart").length).toBeGreaterThan(0);
    expect(screen.getByText("hello page")).toBeInTheDocument();
  });

  it("hides modules the role may not use, rather than disabling them", () => {
    render(
      <AppShell role="staff" tenantName="Ali Mart">
        <p>x</p>
      </AppShell>,
    );
    const nav = screen.getByRole("navigation", { name: /main/i });
    expect(within(nav).queryByText("Finance")).toBeNull();
    expect(within(nav).queryByText("Settings")).toBeNull();
    expect(within(nav).getByText("Sales")).toBeInTheDocument();
  });

  it("marks the current page for assistive technology", () => {
    render(
      <AppShell role="owner" tenantName="Ali Mart" activeHref="/dashboard">
        <p>x</p>
      </AppShell>,
    );
    const nav = screen.getByRole("navigation", { name: /main/i });
    expect(within(nav).getByRole("link", { name: /home/i })).toHaveAttribute("aria-current", "page");
  });

  it("gives every icon-only control an accessible name", () => {
    render(
      <AppShell role="owner" tenantName="Ali Mart">
        <p>x</p>
      </AppShell>,
    );
    for (const button of screen.getAllByRole("button")) {
      expect(button.getAttribute("aria-label") || button.textContent?.trim()).toBeTruthy();
    }
  });

  it("has a phone tab bar with the five primary destinations", () => {
    render(
      <AppShell role="owner" tenantName="Ali Mart">
        <p>x</p>
      </AppShell>,
    );
    const bar = screen.getByRole("navigation", { name: /primary tabs/i });
    expect(within(bar).getAllByRole("link").length + within(bar).queryAllByRole("button").length).toBe(5);
  });
});

describe("AppShell phone tab bar and roles", () => {
  it("does not offer staff a page the sidebar hides", () => {
    render(
      <AppShell role="staff" tenantName="Ali Mart">
        <p>x</p>
      </AppShell>,
    );
    const bar = screen.getByRole("navigation", { name: /primary tabs/i });
    expect(within(bar).queryByRole("link", { name: /inbox/i })).toBeNull();
    expect(within(bar).getByRole("link", { name: /orders/i })).toBeInTheDocument();
  });
});
