import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LanguageSwitcher } from "@/components/app/LanguageSwitcher";
import { PageHeader } from "@/components/app/PageHeader";
import { StatusBadge } from "@/components/app/StatusBadge";
import { dirFor, translate } from "@/lib/i18n/dictionary";
import { LocaleProvider } from "@/lib/i18n/LocaleProvider";

describe("the dictionary (PRD §16)", () => {
  it("returns the English text unchanged, and Urdu for a known string", () => {
    expect(translate("en", "Orders")).toBe("Orders");
    expect(translate("ur", "Orders")).toBe("آرڈرز");
  });

  it("falls back to the English original when a string has no translation, never to a blank or a key", () => {
    expect(translate("ur", "A sentence nobody translated yet")).toBe("A sentence nobody translated yet");
    expect(translate("ur", "")).toBe("");
  });

  it("writes Urdu right to left and English left to right", () => {
    expect(dirFor("ur")).toBe("rtl");
    expect(dirFor("en")).toBe("ltr");
  });
});

describe("switching the language", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.lang = "en";
    document.documentElement.dir = "ltr";
  });
  afterEach(() => window.localStorage.clear());

  function Screen() {
    return (
      <LocaleProvider>
        <LanguageSwitcher />
        <PageHeader title="Orders" description="A description that has no translation." />
        <StatusBadge status="posted" />
      </LocaleProvider>
    );
  }

  it("starts in English, left to right", () => {
    render(<Screen />);
    expect(screen.getByRole("heading", { name: "Orders" })).toBeInTheDocument();
    expect(document.documentElement.dir).toBe("ltr");
  });

  it("Urdu flips the document to right to left, translates what it knows and leaves the rest in English", async () => {
    render(<Screen />);
    await userEvent.click(screen.getByRole("button", { name: "اردو" }));
    expect(await screen.findByRole("heading", { name: "آرڈرز" })).toBeInTheDocument();
    await waitFor(() => expect(document.documentElement.dir).toBe("rtl"));
    expect(document.documentElement.lang).toBe("ur");
    expect(screen.getByText("A description that has no translation.")).toBeInTheDocument();
    expect(screen.getByText("پوسٹ ہو گیا")).toBeInTheDocument(); // a status badge
    expect(window.localStorage.getItem("bf_locale")).toBe("ur");
  });

  it("switching back restores English and left to right", async () => {
    render(<Screen />);
    await userEvent.click(screen.getByRole("button", { name: "اردو" }));
    await userEvent.click(screen.getByRole("button", { name: "English" }));
    expect(await screen.findByRole("heading", { name: "Orders" })).toBeInTheDocument();
    await waitFor(() => expect(document.documentElement.dir).toBe("ltr"));
  });

  it("still switches for this visit when the browser refuses to store the choice", async () => {
    const blocked = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    render(<Screen />);
    await userEvent.click(screen.getByRole("button", { name: "اردو" }));
    expect(await screen.findByRole("heading", { name: "آرڈرز" })).toBeInTheDocument();
    blocked.mockRestore();
  });
});
