import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/client";
import type { OrderDetail, Product, SalePreview } from "@/lib/api/types";

const apiGet = vi.fn();
const apiPost = vi.fn();
const push = vi.fn();
vi.mock("@/lib/api/client", async (original) => ({
  ...(await original<typeof import("@/lib/api/client")>()),
  apiGet: (...a: unknown[]) => apiGet(...a),
  apiPost: (...a: unknown[]) => apiPost(...a),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
let role: "owner" | "manager" | "staff" = "staff";
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ role }) }));

import { SaleForm } from "@/components/sales/SaleForm";

const shirt: Product = {
  id: "p1",
  tenant_id: "t1",
  sku: "SHIRT-1",
  name: "Classic Shirt",
  category: null,
  price: "2500.00",
  cost: null,
  vendor_id: null,
  image_url: null,
  active: true,
  qty_on_hand: 3,
  reorder_level: 0,
  low_stock: false,
  created_at: "2026-10-01T10:00:00Z",
  updated_at: "2026-10-01T10:00:00Z",
};

const previewFor = (over: Partial<SalePreview> = {}): SalePreview => ({
  lines: [{ product_id: "p1", product_name: "Classic Shirt", unit_price: "2500.00", line_total: "2500.00", available: 3, enough_stock: true }],
  subtotal: "2500.00",
  discount: "0.00",
  total: "2500.00",
  amount_paid: "2500.00",
  amount_due: "0.00",
  warnings: [],
  ...over,
});

const order = { id: "o-1", total: "2500.00", amount_due: "0.00" } as OrderDetail;

function route(preview: SalePreview = previewFor()) {
  apiGet.mockResolvedValue({ items: [shirt], total: 1, next_cursor: null });
  apiPost.mockImplementation((path: string) => (path === "/sales/preview" ? Promise.resolve(preview) : Promise.resolve(order)));
}

async function addShirt() {
  await userEvent.click(screen.getByRole("button", { name: "Add product" }));
  await userEvent.click(await screen.findByRole("button", { name: /Classic Shirt/ }));
}

beforeEach(() => {
  apiGet.mockReset();
  apiPost.mockReset();
  push.mockReset();
  role = "staff";
});

describe("New sale (PRD F-007)", () => {
  it("starts empty, explains what to do, and will not post without an item", async () => {
    route();
    render(<SaleForm />);
    expect(screen.getByText("No items yet. Use Add product to start the sale.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Post sale" }));
    expect(await screen.findByText("Add at least one item to the sale")).toBeInTheDocument();
    expect(apiPost).not.toHaveBeenCalledWith("/sales/", expect.anything(), expect.anything());
  });

  it("adds a product from the search dialog, and every total on screen comes from the server", async () => {
    route();
    render(<SaleForm />);
    await addShirt();
    expect(screen.getByLabelText("Quantity of Classic Shirt")).toHaveValue("1");
    const totals = await screen.findByRole("group", { name: "Sale totals" }).catch(() => screen.getByLabelText("Sale totals"));
    await waitFor(() => expect(within(totals).getByText("Total").nextElementSibling).toHaveTextContent("Rs 2,500"));
    expect(apiPost).toHaveBeenCalledWith("/sales/preview", expect.objectContaining({ items: [{ product_id: "p1", qty: 1, unit_price: "2500.00" }] }));
  });

  it("adding the same product again adds one more instead of a second line", async () => {
    route();
    render(<SaleForm />);
    await addShirt();
    await addShirt();
    expect(screen.getAllByLabelText("Quantity of Classic Shirt")).toHaveLength(1);
    expect(screen.getByLabelText("Quantity of Classic Shirt")).toHaveValue("2");
  });

  it("explains a bad quantity or price at the line", async () => {
    route();
    render(<SaleForm />);
    await addShirt();
    await userEvent.clear(screen.getByLabelText("Quantity of Classic Shirt"));
    await userEvent.type(screen.getByLabelText("Quantity of Classic Shirt"), "0");
    await waitFor(() => expect(screen.getByRole("button", { name: "Post sale" })).toBeEnabled());
    await userEvent.click(screen.getByRole("button", { name: "Post sale" }));
    expect(await screen.findByText("Quantity of Classic Shirt must be a whole number above zero")).toBeInTheDocument();
    expect(apiPost).not.toHaveBeenCalledWith("/sales/", expect.anything(), expect.anything());
  });

  it("a sale on credit needs a customer", async () => {
    route(previewFor({ amount_paid: "0.00", amount_due: "2500.00" }));
    render(<SaleForm />);
    await addShirt();
    await userEvent.selectOptions(screen.getByLabelText(/^Paid by/), "udhaar");
    await waitFor(() => expect(screen.getByRole("button", { name: "Post sale" })).toBeEnabled());
    await userEvent.click(screen.getByRole("button", { name: "Post sale" }));
    expect(await screen.findByText(/Choose the customer/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Amount received/)).toBeDisabled();
  });

  it("posts once for a double click, with an Idempotency-Key, then opens the order", async () => {
    route();
    render(<SaleForm />);
    await addShirt();
    await waitFor(() => expect(screen.getByRole("button", { name: "Post sale" })).toBeEnabled());
    await userEvent.dblClick(screen.getByRole("button", { name: "Post sale" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/orders/o-1"));
    const posts = apiPost.mock.calls.filter((c) => c[0] === "/sales/");
    expect(posts).toHaveLength(1);
    expect(posts[0][2]).toEqual({ "Idempotency-Key": expect.stringMatching(/.{8,}/) });
    expect(posts[0][1]).toMatchObject({ payment_method: "cash", stock_override: false, customer_id: null });
  });

  it("shows the server's refusal in words and keeps the sale so it can be fixed", async () => {
    route();
    apiPost.mockImplementation((path: string) =>
      path === "/sales/preview" ? Promise.resolve(previewFor()) : Promise.reject(new ApiError(422, "Not enough stock for Classic Shirt: 3 on hand, 5 needed", "insufficient_stock")),
    );
    render(<SaleForm />);
    await addShirt();
    await waitFor(() => expect(screen.getByRole("button", { name: "Post sale" })).toBeEnabled());
    await userEvent.click(screen.getByRole("button", { name: "Post sale" }));
    expect(await screen.findByText("Not enough stock for Classic Shirt: 3 on hand, 5 needed")).toBeInTheDocument();
    expect(screen.getByLabelText("Quantity of Classic Shirt")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("only a manager is offered the stock override, and only when the shelf is short", async () => {
    const short = previewFor({
      lines: [{ product_id: "p1", product_name: "Classic Shirt", unit_price: "2500.00", line_total: "12500.00", available: 3, enough_stock: false }],
      warnings: ["Not enough stock for Classic Shirt: 3 on hand, 5 needed"],
    });
    route(short);
    role = "staff";
    const staff = render(<SaleForm />);
    await addShirt();
    expect(await screen.findByText("Not enough stock for Classic Shirt: 3 on hand, 5 needed")).toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: /Sell more than the shelf count/ })).not.toBeInTheDocument();
    staff.unmount();

    route(short);
    role = "manager";
    render(<SaleForm />);
    await addShirt();
    expect(await screen.findByRole("checkbox", { name: /Sell more than the shelf count/ })).toBeInTheDocument();
  });
});
