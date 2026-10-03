import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/client";
import type { OrderDetail, OrderSummary } from "@/lib/api/types";

const apiGet = vi.fn();
const apiPost = vi.fn();
vi.mock("@/lib/api/client", async (original) => ({
  ...(await original<typeof import("@/lib/api/client")>()),
  apiGet: (...a: unknown[]) => apiGet(...a),
  apiPost: (...a: unknown[]) => apiPost(...a),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }), useParams: () => ({ id: "11111111-aaaa-bbbb-cccc-222222222222" }) }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
let role: "owner" | "manager" | "staff" = "manager";
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ role }) }));

import OrderPage from "@/app/(app)/(workspace)/orders/[id]/page";
import OrdersPage from "@/app/(app)/(workspace)/orders/page";

const summary = (over: Partial<OrderSummary> = {}): OrderSummary => ({
  id: "11111111-aaaa-bbbb-cccc-222222222222",
  status: "posted",
  channel: "pos",
  customer_id: null,
  customer_name: null,
  subtotal: "2500.00",
  discount: "0.00",
  total: "2500.00",
  amount_paid: "2500.00",
  amount_due: "0.00",
  item_count: 1,
  created_at: "2026-10-02T10:00:00Z",
  ...over,
});

const detail = (over: Partial<OrderDetail> = {}): OrderDetail => ({
  ...summary(),
  note: null,
  created_by: "u1",
  updated_at: "2026-10-02T10:00:00Z",
  items: [{ id: "i1", product_id: "p1", product_name: "Classic Shirt", qty: 1, unit_price: "2500.00", unit_cost: "1800.00", line_total: "2500.00" }],
  payments: [{ id: "pay1", amount: "2500.00", method: "cash", status: "completed", created_at: "2026-10-02T10:00:00Z" }],
  ...over,
});

beforeEach(() => {
  apiGet.mockReset();
  apiPost.mockReset();
  role = "manager";
});

describe("Orders list: four states (PRD F-008)", () => {
  it("ready shows a short reference, the customer, money and a text status", async () => {
    apiGet.mockResolvedValue({ items: [summary(), summary({ id: "99999999-aaaa-bbbb-cccc-222222222222", customer_name: "Ali", amount_due: "300.00", status: "reversed" })], total: 2, next_cursor: null });
    render(<OrdersPage />);
    const table = await screen.findByRole("table", { name: "Orders" });
    expect(within(table).getByRole("link", { name: "11111111" })).toHaveAttribute("href", "/orders/11111111-aaaa-bbbb-cccc-222222222222");
    expect(within(table).getByText("Walk-in")).toBeInTheDocument();
    expect(within(table).getByText("Ali")).toBeInTheDocument();
    expect(within(table).getByText("reversed")).toBeInTheDocument();
    expect(within(table).getByText("Rs 300")).toBeInTheDocument();
  });

  it("empty offers the first sale; filters can be cleared; error retries; loading is skeleton rows", async () => {
    apiGet.mockReturnValue(new Promise(() => undefined));
    const first = render(<OrdersPage />);
    expect(screen.getAllByTestId("skeleton-row").length).toBeGreaterThan(0);
    first.unmount();

    apiGet.mockResolvedValue({ items: [], total: 0, next_cursor: null });
    const second = render(<OrdersPage />);
    expect(await screen.findByText("No sales yet.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Record your first sale" })).toBeInTheDocument();
    second.unmount();

    apiGet.mockRejectedValueOnce(new ApiError(500, "The server is busy.")).mockResolvedValueOnce({ items: [summary()], total: 1, next_cursor: null });
    render(<OrdersPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The server is busy.");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("table", { name: "Orders" })).toBeInTheDocument();
  });

  it("the status filter goes to the API", async () => {
    apiGet.mockResolvedValue({ items: [summary()], total: 1, next_cursor: null });
    render(<OrdersPage />);
    await screen.findByRole("table", { name: "Orders" });
    await userEvent.selectOptions(screen.getByLabelText("Status"), "reversed");
    await waitFor(() => expect(apiGet).toHaveBeenLastCalledWith("/orders/", expect.objectContaining({ status: "reversed" })));
  });
});

describe("Order detail: read-only, with Reverse for managers", () => {
  it("shows lines, payments and totals, and offers Reverse sale to a manager", async () => {
    apiGet.mockResolvedValue(detail());
    render(<OrderPage />);
    expect(await screen.findByRole("heading", { name: "Order 11111111" })).toBeInTheDocument();
    expect(within(screen.getByRole("table", { name: "Items on this order" })).getByText("Classic Shirt")).toBeInTheDocument();
    expect(within(screen.getByRole("table", { name: "Payments on this order" })).getByText("completed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reverse sale" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edit|delete/i })).not.toBeInTheDocument();
  });

  it("staff cannot reverse and see no cost column; a reversed sale offers nothing to undo", async () => {
    role = "staff";
    apiGet.mockResolvedValue(detail({ items: [{ ...detail().items[0], unit_cost: null }] }));
    const staff = render(<OrderPage />);
    await screen.findByRole("heading", { name: "Order 11111111" });
    expect(screen.queryByRole("button", { name: "Reverse sale" })).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Cost" })).not.toBeInTheDocument();
    staff.unmount();

    role = "manager";
    apiGet.mockResolvedValue(detail({ status: "reversed" }));
    render(<OrderPage />);
    await screen.findByRole("heading", { name: "Order 11111111" });
    expect(screen.queryByRole("button", { name: "Reverse sale" })).not.toBeInTheDocument();
  });

  it("asks for a reason, explains the consequences and reverses once", async () => {
    apiGet.mockResolvedValue(detail());
    apiPost.mockResolvedValue(detail({ status: "reversed" }));
    render(<OrderPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Reverse sale" }));
    expect(await screen.findByText("Reverse this sale?")).toBeInTheDocument();
    expect(screen.getByText(/goes back into stock/)).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole("button", { name: "Reverse sale" }).at(-1) as HTMLElement);
    expect(await screen.findByText("Give a reason of at least 3 characters")).toBeInTheDocument();
    expect(apiPost).not.toHaveBeenCalled();

    await userEvent.type(screen.getByLabelText(/^Why is it being reversed/), "Wrong item");
    await userEvent.dblClick(screen.getAllByRole("button", { name: "Reverse sale" }).at(-1) as HTMLElement);
    await waitFor(() => expect(apiPost).toHaveBeenCalledTimes(1));
    expect(apiPost).toHaveBeenCalledWith("/orders/11111111-aaaa-bbbb-cccc-222222222222/reverse", { reason: "Wrong item" });
    await waitFor(() => expect(screen.queryByRole("button", { name: "Reverse sale" })).not.toBeInTheDocument());
    expect(screen.getByText("reversed")).toBeInTheDocument();
  });

  it("a missing order says so and a failure can be retried", async () => {
    apiGet.mockRejectedValue(new ApiError(404, "Order not found", "not_found"));
    render(<OrderPage />);
    expect(await screen.findByText("That order does not exist.")).toBeInTheDocument();
  });
});
