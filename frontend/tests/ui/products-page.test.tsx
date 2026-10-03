import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/client";
import type { Product } from "@/lib/api/types";

const apiGet = vi.fn();
vi.mock("@/lib/api/client", async (original) => ({
  ...(await original<typeof import("@/lib/api/client")>()),
  apiGet: (...a: unknown[]) => apiGet(...a),
}));
let role: "owner" | "manager" | "staff" = "manager";
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ role }) }));

import ProductsPage from "@/app/(app)/(workspace)/inventory/page";

const product = (over: Partial<Product> = {}): Product => ({
  id: "p1",
  tenant_id: "t1",
  sku: "SHIRT-1",
  name: "Classic Shirt",
  category: "Apparel",
  price: "2500.00",
  cost: "1800.00",
  vendor_id: null,
  image_url: null,
  active: true,
  qty_on_hand: 12,
  reorder_level: 5,
  low_stock: false,
  created_at: "2026-10-01T10:00:00Z",
  updated_at: "2026-10-01T10:00:00Z",
  ...over,
});

beforeEach(() => {
  apiGet.mockReset();
  role = "manager";
});

describe("Products list: four states and roles (PRD F-010, ui-rules.md)", () => {
  it("loading shows skeleton rows, not a spinner", () => {
    apiGet.mockReturnValue(new Promise(() => undefined));
    render(<ProductsPage />);
    expect(screen.getAllByTestId("skeleton-row").length).toBeGreaterThan(0);
  });

  it("ready shows formatted money, a status badge and the cost column for a manager", async () => {
    apiGet.mockResolvedValue({
      items: [product(), product({ id: "p2", sku: "JEANS-2", name: "Denim", qty_on_hand: 2, low_stock: true })],
      total: 2,
      next_cursor: null,
    });
    render(<ProductsPage />);
    const table = await screen.findByRole("table", { name: "Products" });
    expect(within(table).getAllByText("Rs 2,500").length).toBeGreaterThan(0);
    expect(within(table).getByText("low stock")).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Cost" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add product" })).toHaveAttribute("href", "/inventory/new");
  });

  it("staff see no cost column and no Add product button", async () => {
    role = "staff";
    apiGet.mockResolvedValue({ items: [product({ cost: null })], total: 1, next_cursor: null });
    render(<ProductsPage />);
    await screen.findByRole("table", { name: "Products" });
    expect(screen.queryByRole("columnheader", { name: "Cost" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Add product" })).not.toBeInTheDocument();
  });

  it("empty explains why and offers the fixing action", async () => {
    apiGet.mockResolvedValue({ items: [], total: 0, next_cursor: null });
    render(<ProductsPage />);
    expect(await screen.findByText("You have not added any products yet.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add your first product" })).toBeInTheDocument();
  });

  it("error says what failed and retries on request", async () => {
    apiGet
      .mockRejectedValueOnce(new ApiError(500, "The database is busy."))
      .mockResolvedValueOnce({ items: [product()], total: 1, next_cursor: null });
    render(<ProductsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The database is busy.");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Classic Shirt")).toBeInTheDocument();
  });

  it("unauthorized explains the restriction instead of a blank page", async () => {
    apiGet.mockRejectedValue(new ApiError(403, "Not allowed"));
    render(<ProductsPage />);
    expect(await screen.findByText("Access is restricted")).toBeInTheDocument();
  });

  it("the low-stock filter and paging go to the API", async () => {
    apiGet.mockResolvedValue({ items: [product()], total: 40, next_cursor: "abc" });
    render(<ProductsPage />);
    await screen.findByText("Classic Shirt");
    await userEvent.click(screen.getByRole("checkbox", { name: "Low stock only" }));
    await waitFor(() => expect(apiGet).toHaveBeenLastCalledWith("/inventory/", expect.objectContaining({ low_stock: true })));
    await userEvent.click(await screen.findByRole("button", { name: "Next" }));
    await waitFor(() => expect(apiGet).toHaveBeenLastCalledWith("/inventory/", expect.objectContaining({ cursor: "abc" })));
    await waitFor(() => expect(screen.getByRole("button", { name: "Previous" })).toBeEnabled());
  });
});
