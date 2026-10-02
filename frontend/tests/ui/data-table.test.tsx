import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DataTable, type Column } from "@/components/app/DataTable";

type Row = { sku: string; name: string; qty: number; price: string; status: string };

const columns: Column<Row>[] = [
  { key: "sku", header: "SKU", mono: true },
  { key: "name", header: "Name" },
  { key: "qty", header: "Qty", numeric: true },
  { key: "price", header: "Price", money: true },
  { key: "status", header: "Status", status: true },
];
const rows: Row[] = [{ sku: "S-1", name: "Shirt", qty: 5, price: "2500", status: "posted" }];

describe("DataTable: four states, every time (ui-rules.md)", () => {
  it("renders rows with money formatted, numbers right-aligned and status as a text badge", () => {
    render(<DataTable caption="Products" columns={columns} rows={rows} state="ready" />);
    const table = screen.getByRole("table", { name: "Products" });
    expect(within(table).getByText("Rs 2,500")).toBeInTheDocument();
    expect(within(table).getByText("posted")).toBeInTheDocument();
    expect(within(table).getByText("5").className).toMatch(/text-right/);
    expect(within(table).getByText("Rs 2,500").className).toMatch(/text-right/);
    expect(within(table).getByText("S-1").className).toMatch(/font-mono/);
  });

  it("scrolls horizontally inside its own container, never the page", () => {
    render(<DataTable caption="Products" columns={columns} rows={rows} state="ready" />);
    expect(screen.getByTestId("table-scroll").className).toMatch(/overflow-x-auto/);
  });

  it("loading: skeleton rows that match the layout, not a spinner", () => {
    render(<DataTable caption="Products" columns={columns} rows={[]} state="loading" />);
    expect(screen.getByRole("table", { name: "Products" })).toHaveAttribute("aria-busy", "true");
    expect(screen.getAllByTestId("skeleton-row").length).toBeGreaterThanOrEqual(3);
  });

  it("empty: explains why and offers the action that fixes it", async () => {
    const onClick = vi.fn();
    render(
      <DataTable
        caption="Products"
        columns={columns}
        rows={[]}
        state="empty"
        emptyMessage="No products yet."
        emptyAction={{ label: "Add product", onClick }}
      />,
    );
    expect(screen.getByText("No products yet.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Add product" }));
    expect(onClick).toHaveBeenCalled();
  });

  it("error: says what failed and offers retry, without a stack trace", async () => {
    const onRetry = vi.fn();
    render(
      <DataTable
        caption="Products"
        columns={columns}
        rows={[]}
        state="error"
        errorMessage="Could not load products."
        onRetry={onRetry}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Could not load products.");
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("unauthorized: explains that access is restricted instead of a blank screen", () => {
    render(<DataTable caption="Finance" columns={columns} rows={[]} state="unauthorized" />);
    expect(screen.getByText(/restricted/i)).toBeInTheDocument();
  });
});
