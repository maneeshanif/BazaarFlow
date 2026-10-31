import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { Chapters } from "@/components/site/Chapters";
import { Cursor } from "@/components/site/Cursor";
import { MenuTab } from "@/components/site/MenuTab";

const LINKS = [
  { label: "How it works", href: "/#how" },
  { label: "Live demo", href: "/demo" },
];

/** jsdom has no matchMedia: answer only the queries a test cares about. */
function media(matching: string[]) {
  window.matchMedia = ((query: string) =>
    ({ matches: matching.some((m) => query.includes(m)), media: query, onchange: null, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent: () => false }) as MediaQueryList) as typeof window.matchMedia;
}

afterEach(() => {
  document.documentElement.classList.remove("has-cursor");
});

describe("Pull-tab menu (public site)", () => {
  it("starts put away, with its links out of the tab order, and the tab says Menu", () => {
    render(<MenuTab links={LINKS} />);
    const tab = screen.getByRole("button", { name: "Menu" });
    expect(tab).toHaveAttribute("aria-expanded", "false");
    expect(document.getElementById(tab.getAttribute("aria-controls") as string)).toHaveAttribute("inert");
  });

  it("opens when the tab is pulled, names the destinations once each and closes on Escape", () => {
    render(<MenuTab links={LINKS} />);
    fireEvent.click(screen.getByRole("button", { name: "Menu" }));
    const tab = screen.getByRole("button", { name: "Close" });
    expect(tab).toHaveAttribute("aria-expanded", "true");
    expect(document.getElementById(tab.getAttribute("aria-controls") as string)).not.toHaveAttribute("inert");
    expect(screen.getByRole("link", { name: "How it works" })).toHaveAttribute("href", "/#how");
    expect(screen.getByRole("link", { name: "Live demo" })).toHaveAttribute("href", "/demo");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.getByRole("button", { name: "Menu" })).toHaveAttribute("aria-expanded", "false");
  });

  it("closes when a link is followed", () => {
    render(<MenuTab links={LINKS} />);
    fireEvent.click(screen.getByRole("button", { name: "Menu" }));
    fireEvent.click(screen.getByRole("link", { name: "Live demo" }));
    expect(screen.getByRole("button", { name: "Menu" })).toHaveAttribute("aria-expanded", "false");
  });
});

describe("Arrow cursor (public site)", () => {
  it("takes over the cursor for a fine pointer and turns into a hand over a link", () => {
    media(["pointer: fine"]);
    render(
      <>
        <Cursor />
        <a href="/demo">Demo</a>
      </>,
    );
    expect(document.documentElement).toHaveClass("has-cursor");
    const arrow = screen.getByTestId("cursor-arrow");
    fireEvent.pointerMove(window, { clientX: 40, clientY: 50 });
    expect(arrow).toHaveAttribute("data-show", "1");
    fireEvent.pointerOver(screen.getByRole("link", { name: "Demo" }));
    expect(arrow).toHaveAttribute("data-hand", "1");
    fireEvent.pointerOver(document.body);
    expect(arrow).toHaveAttribute("data-hand", "0");
  });

  it("leaves the system cursor alone for touch and for reduced motion", () => {
    media(["prefers-reduced-motion"]);
    render(<Cursor />);
    expect(document.documentElement).not.toHaveClass("has-cursor");
    media([]);
    render(<Cursor />);
    expect(document.documentElement).not.toHaveClass("has-cursor");
  });
});

describe("Chapters (disc slider)", () => {
  it("shows the first chapter, keeps the others in the page but hidden, and switches by disc or arrow key", () => {
    render(<Chapters />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(4);
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText(/Example: the shopkeeper writes/)).toBeInTheDocument();
    fireEvent.click(tabs[1]);
    expect(tabs[1]).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(tabs[1], { key: "ArrowDown" });
    expect(tabs[2]).toHaveAttribute("aria-selected", "true");
    expect(screen.getAllByRole("tabpanel", { hidden: false })).toHaveLength(1);
  });
});
