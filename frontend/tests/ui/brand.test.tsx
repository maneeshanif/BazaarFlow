import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BrandImage } from "@/components/brand/BrandImage";
import { Chip } from "@/components/brand/Chip";
import { SplitHeading } from "@/components/site/motion";

describe("Brand artwork placeholders (ADR 0005)", () => {
  it("draws a coloured placeholder with the label when the file is missing", () => {
    render(<BrandImage file="hero-roll.png" alt="A roll of tape" label="Hero roll" tone="forest" />);
    fireEvent.error(screen.getByRole("img", { name: "A roll of tape" }));
    const placeholder = screen.getByRole("img", { name: "A roll of tape" });
    expect(placeholder).toHaveAttribute("data-placeholder", "hero-roll.png");
    expect(placeholder).toHaveTextContent("Hero roll");
  });

  it("hides decorative artwork from assistive technology, image or placeholder", () => {
    const { container } = render(<BrandImage file="roll-sales.png" alt="" decorative label="Sales" />);
    const img = container.querySelector("img");
    expect(img).toHaveAttribute("aria-hidden", "true");
    fireEvent.error(img as HTMLImageElement);
    expect(container.querySelector("[data-placeholder]")).toHaveAttribute("aria-hidden", "true");
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("serves the file from public/brand", () => {
    render(<BrandImage file="logo-badge.png" alt="BazaarFlow" />);
    expect(screen.getByRole("img", { name: "BazaarFlow" })).toHaveAttribute("src", "/brand/logo-badge.png");
  });
});

describe("Display headings", () => {
  it("expose the text once, whole, to assistive technology while the split letters are decoration", () => {
    render(<SplitHeading as="h1" text="Tell it what you sold" />);
    const heading = screen.getByRole("heading", { level: 1, name: "Tell it what you sold" });
    expect(heading.querySelector(".sr-only")).toHaveTextContent("Tell it what you sold");
    expect(heading.querySelector("[aria-hidden]")).not.toBeNull();
  });

  it("keeps the chip label readable", () => {
    render(<Chip>Highlight</Chip>);
    expect(screen.getByText("Highlight")).toBeInTheDocument();
  });
});
