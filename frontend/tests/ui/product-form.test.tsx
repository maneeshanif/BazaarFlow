import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/client";
import type { Product } from "@/lib/api/types";

const apiPost = vi.fn();
const apiPatch = vi.fn();
const push = vi.fn();
vi.mock("@/lib/api/client", async (original) => ({
  ...(await original<typeof import("@/lib/api/client")>()),
  apiPost: (...a: unknown[]) => apiPost(...a),
  apiPatch: (...a: unknown[]) => apiPatch(...a),
  apiDelete: vi.fn(),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
let role: "owner" | "manager" = "owner";
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ role }) }));

import { ProductForm } from "@/components/inventory/ProductForm";

const saved: Product = {
  id: "p1",
  tenant_id: "t1",
  sku: "SKU-1",
  name: "Classic Shirt",
  category: null,
  price: "2500.00",
  cost: null,
  vendor_id: null,
  image_url: null,
  active: true,
  qty_on_hand: 5,
  reorder_level: 0,
  low_stock: false,
  created_at: "2026-10-01T10:00:00Z",
  updated_at: "2026-10-01T10:00:00Z",
};

async function fillValid() {
  await userEvent.type(screen.getByLabelText(/^SKU/), "SKU-1");
  await userEvent.type(screen.getByLabelText(/^Name/), "Classic Shirt");
  await userEvent.type(screen.getByLabelText(/^Price/), "2500");
}

beforeEach(() => {
  apiPost.mockReset();
  apiPatch.mockReset();
  push.mockReset();
  role = "owner";
});

describe("ProductForm (task 52: validation, errors, double-submit)", () => {
  it("shows inline messages under the fields and sends nothing when the input is invalid", async () => {
    render(<ProductForm />);
    await userEvent.click(screen.getByRole("button", { name: "Add product" }));
    expect(await screen.findByText("SKU is required")).toBeInTheDocument();
    expect(screen.getByText("Name needs at least 2 characters")).toBeInTheDocument();
    expect(screen.getByLabelText(/^SKU/)).toHaveAttribute("aria-invalid", "true");
    expect(apiPost).not.toHaveBeenCalled();
  });

  it("validates a field only after it was visited, and clears the message as soon as it is valid", async () => {
    render(<ProductForm />);
    await userEvent.type(screen.getByLabelText(/^SKU/), "A");
    await userEvent.tab();
    // leaving SKU must not scold the fields the person has not reached yet
    expect(screen.queryByText("Name needs at least 2 characters")).not.toBeInTheDocument();
    await userEvent.click(screen.getByLabelText(/^Name/));
    await userEvent.tab();
    expect(await screen.findByText("Name needs at least 2 characters")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/^Name/), "Shirt");
    await waitFor(() => expect(screen.queryByText("Name needs at least 2 characters")).not.toBeInTheDocument());
  });

  it("a double click on Add product creates one record", async () => {
    let release: (p: Product) => void = () => undefined;
    apiPost.mockReturnValue(new Promise<Product>((resolve) => (release = resolve)));
    render(<ProductForm />);
    await fillValid();
    const button = screen.getByRole("button", { name: "Add product" });
    await userEvent.dblClick(button);
    expect(apiPost).toHaveBeenCalledTimes(1);
    expect(button).toBeDisabled();
    release(saved);
    await waitFor(() => expect(push).toHaveBeenCalledWith("/inventory"));
    expect(apiPost).toHaveBeenCalledTimes(1);
  });

  it("puts the server's duplicate-SKU message under the SKU field", async () => {
    apiPost.mockRejectedValue(new ApiError(409, "A product with SKU SKU-1 already exists", "duplicate_sku"));
    render(<ProductForm />);
    await fillValid();
    await userEvent.click(screen.getByRole("button", { name: "Add product" }));
    expect(await screen.findByText("A product with SKU SKU-1 already exists")).toBeInTheDocument();
    expect(screen.getByLabelText(/^SKU/)).toHaveAttribute("aria-invalid", "true");
  });

  it("when editing, quantity is read-only and deleting names the product and asks first", async () => {
    render(<ProductForm product={saved} />);
    expect(screen.getByLabelText(/^In stock/)).toHaveAttribute("readonly");
    await userEvent.click(screen.getByRole("button", { name: "Delete product" }));
    expect(await screen.findByText("Delete Classic Shirt?")).toBeInTheDocument();
  });

  it("only the owner is offered Delete", () => {
    role = "manager";
    render(<ProductForm product={saved} />);
    expect(screen.queryByRole("button", { name: "Delete product" })).not.toBeInTheDocument();
  });
});
