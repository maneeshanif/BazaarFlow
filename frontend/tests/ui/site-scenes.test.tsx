import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Chapters } from "@/components/site/Chapters";
import { ContactForm } from "@/components/site/ContactForm";
import { Cursor } from "@/components/site/Cursor";
import { MenuTab } from "@/components/site/MenuTab";
import { NewsList, type NewsItem } from "@/components/site/NewsList";
import { CharText, RollLabel, WordText } from "@/components/site/text";

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


describe("Text engine", () => {
  it("exposes a heading, a paragraph and a rolling label once, whole, while the letters are decoration", () => {
    const { container } = render(
      <>
        <CharText text="Pick your tool" />
        <WordText text="Six parts of one back-office." />
        <RollLabel text="Live demo" />
      </>,
    );
    expect(screen.getByRole("heading", { name: "Pick your tool" })).toBeInTheDocument();
    expect(screen.getByText("Six parts of one back-office.", { selector: ".sr-only" })).toBeInTheDocument();
    expect(screen.getByText("Live demo", { selector: ".sr-only" })).toBeInTheDocument();
    // every drawn letter is hidden from assistive technology
    expect(container.querySelectorAll("[aria-hidden] [data-char]").length).toBe("Pickyourtool".length);
  });

  it("lifts the letters near the pointer and lets them settle when it leaves (fine pointer only)", () => {
    media(["pointer: fine"]);
    vi.useFakeTimers({ toFake: ["requestAnimationFrame", "cancelAnimationFrame"] });
    const { container } = render(<CharText text="Hello" reveal={false} />);
    const root = container.querySelector("span") as HTMLElement;
    const letters = [...container.querySelectorAll<HTMLElement>("[data-char]")];
    // jsdom has no layout: give every clip a box so the distances mean something
    letters.forEach((l, i) => {
      (l.parentElement as HTMLElement).getBoundingClientRect = () => ({ left: i * 40, top: 0, width: 40, height: 40, right: i * 40 + 40, bottom: 40, x: i * 40, y: 0, toJSON() {} }) as DOMRect;
    });
    act(() => {
      fireEvent.pointerMove(root, { clientX: 100, clientY: 20, pointerType: "mouse" });
      vi.advanceTimersByTime(400);
    });
    expect(letters[2].style.transform).toContain("translate3d");
    expect(letters[0].style.transform === "" || !letters[0].style.transform.includes("-0.")).toBe(true);
    act(() => {
      fireEvent.pointerLeave(root);
      vi.advanceTimersByTime(3000);
    });
    expect(letters[2].style.transform).toBe("");
    vi.useRealTimers();
  });
});

describe("News filter", () => {
  const items: NewsItem[] = [
    { id: "a", kind: "Update", title: "Shipped one", text: "t", when: "Oct 2026", photo: "x.jpg", tone: "sunny" },
    { id: "b", kind: "Next", title: "Coming one", text: "t", when: "Coming", photo: "x.jpg", tone: "sky" },
  ];
  it("shows everything, then only the chosen kind, and counts each", () => {
    render(<NewsList items={items} />);
    expect(screen.getAllByRole("article")).toHaveLength(2);
    fireEvent.click(screen.getByRole("tab", { name: /Next/ }));
    expect(screen.getAllByRole("article")).toHaveLength(1);
    expect(screen.getByText("Coming one", { selector: "h3" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /All/ })).toHaveTextContent("2");
  });
});

describe("Contact form", () => {
  it("asks for a name and a message before it does anything", () => {
    render(<ContactForm />);
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(screen.getByRole("alert")).toHaveTextContent("name and a message");
  });
});
