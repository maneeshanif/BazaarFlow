import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/client";
import type { Customer, Payment } from "@/lib/api/types";

const apiGet = vi.fn();
const apiPost = vi.fn();
const apiPatch = vi.fn();
const push = vi.fn();
vi.mock("@/lib/api/client", async (original) => ({
  ...(await original<typeof import("@/lib/api/client")>()),
  apiGet: (...a: unknown[]) => apiGet(...a),
  apiPost: (...a: unknown[]) => apiPost(...a),
  apiPatch: (...a: unknown[]) => apiPatch(...a),
  apiDelete: vi.fn(),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
  useParams: () => ({ id: "c1" }),
  usePathname: () => "/customers",
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({ role: "owner", status: "authenticated" }),
}));

import CustomersPage from "@/app/(app)/(workspace)/customers/page";
import { CustomerForm } from "@/components/customers/CustomerForm";
import { LedgerPanel } from "@/components/customers/LedgerPanel";

const customer = (over: Partial<Customer> = {}): Customer => ({
  id: "c1",
  tenant_id: "t1",
  phone: "+923001110001",
  name: "Ali Raza",
  email: null,
  address: "Lahore",
  balance: "1500.50",
  created_at: "2026-10-01T10:00:00Z",
  updated_at: "2026-10-01T10:00:00Z",
  ...over,
});

beforeEach(() => {
  apiGet.mockReset();
  apiPost.mockReset();
  apiPatch.mockReset();
  push.mockReset();
});

describe("Customers list: four states (PRD F-009)", () => {
  it("ready shows what each customer owes, with a text status", async () => {
    apiGet.mockResolvedValue({ items: [customer(), customer({ id: "c2", name: "Bilal", balance: "0.00" })], total: 2, next_cursor: null });
    render(<CustomersPage />);
    const table = await screen.findByRole("table", { name: "Customers" });
    expect(within(table).getByText("Rs 1,500.50")).toBeInTheDocument();
    expect(within(table).getByText("owes")).toBeInTheDocument();
    expect(within(table).getByText("settled")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add customer" })).toHaveAttribute("href", "/customers/new");
  });

  it("empty explains and offers to add; loading is skeleton rows; error retries", async () => {
    apiGet.mockReturnValue(new Promise(() => undefined));
    const { unmount } = render(<CustomersPage />);
    expect(screen.getAllByTestId("skeleton-row").length).toBeGreaterThan(0);
    unmount();

    apiGet.mockResolvedValue({ items: [], total: 0, next_cursor: null });
    const second = render(<CustomersPage />);
    expect(await screen.findByText("You have not added any customers yet.")).toBeInTheDocument();
    second.unmount();

    apiGet.mockRejectedValueOnce(new ApiError(500, "The server is busy.")).mockResolvedValueOnce({ items: [customer()], total: 1, next_cursor: null });
    render(<CustomersPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The server is busy.");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Ali Raza")).toBeInTheDocument();
  });

  it("the owing-only filter goes to the API", async () => {
    apiGet.mockResolvedValue({ items: [customer()], total: 1, next_cursor: null });
    render(<CustomersPage />);
    await screen.findByText("Ali Raza");
    await userEvent.click(screen.getByRole("checkbox", { name: "Owing only" }));
    await waitFor(() => expect(apiGet).toHaveBeenLastCalledWith("/customers/", expect.objectContaining({ owing_only: true })));
  });
});

describe("CustomerForm", () => {
  it("sends a Pakistani number in international form and goes to the new customer", async () => {
    apiPost.mockResolvedValue(customer({ id: "new-1" }));
    render(<CustomerForm />);
    const phone = screen.getByLabelText(/^Phone/);
    await userEvent.clear(phone);
    await userEvent.type(phone, "0300 1110001");
    await userEvent.type(screen.getByLabelText(/^Name/), "Ali Raza");
    await userEvent.click(screen.getByRole("button", { name: "Add customer" }));
    await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/customers/", expect.objectContaining({ phone: "+923001110001", name: "Ali Raza" })));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/customers/new-1"));
  });

  it("explains a bad phone inline and a duplicate under the phone field", async () => {
    render(<CustomerForm />);
    await userEvent.click(screen.getByRole("button", { name: "Add customer" }));
    expect(await screen.findByText("Enter a phone number like 0300 1234567")).toBeInTheDocument();
    expect(apiPost).not.toHaveBeenCalled();

    apiPost.mockRejectedValue(new ApiError(409, "A customer with this phone number already exists", "duplicate_phone"));
    const phone = screen.getByLabelText(/^Phone/);
    await userEvent.clear(phone);
    await userEvent.type(phone, "03001110001");
    await userEvent.click(screen.getByRole("button", { name: "Add customer" }));
    expect(await screen.findByText("A customer with this phone number already exists")).toBeInTheDocument();
  });
});

describe("LedgerPanel: record a payment", () => {
  const payment = (balance: string): Payment => ({ id: "p1", customer_id: "c1", amount: "400.00", method: "cash", created_at: "2026-10-02T10:00:00Z", balance });
  const ledger = { items: [{ id: "e1", direction: "debit", amount: "1500.50", ref_type: "order", ref_id: null, created_at: "2026-10-01T10:00:00Z", balance_after: "1500.50" }], total: 1, next_cursor: null };

  it("shows the balance and the ledger with a running balance", async () => {
    apiGet.mockResolvedValue(ledger);
    render(<LedgerPanel customer={customer()} onChanged={() => undefined} />);
    expect(screen.getByLabelText("Balance")).toHaveTextContent("Rs 1,500.50");
    expect(await screen.findByText("Sale on credit")).toBeInTheDocument();
  });

  it("refuses more than they owe before asking the server, and records one payment for a double click", async () => {
    apiGet.mockResolvedValue(ledger);
    let finish: (p: Payment) => void = () => undefined;
    apiPost.mockReturnValue(new Promise<Payment>((resolve) => (finish = resolve)));
    const changed = vi.fn();
    render(<LedgerPanel customer={customer()} onChanged={changed} />);
    await screen.findByText("Sale on credit");

    await userEvent.type(screen.getByLabelText(/^Amount received/), "9999");
    await userEvent.click(screen.getByRole("button", { name: "Record payment" }));
    expect(await screen.findByText("They only owe Rs 1,500.50")).toBeInTheDocument();
    expect(apiPost).not.toHaveBeenCalled();

    const amount = screen.getByLabelText(/^Amount received/);
    await userEvent.clear(amount);
    await userEvent.type(amount, "400");
    await userEvent.dblClick(screen.getByRole("button", { name: "Record payment" }));
    expect(apiPost).toHaveBeenCalledTimes(1);
    expect(apiPost).toHaveBeenCalledWith("/customers/c1/payments", { amount: "400", method: "cash" });
    finish(payment("1100.50"));
    await waitFor(() => expect(changed).toHaveBeenCalledWith("1100.50"));
  });

  it("hides the payment form for a customer who owes nothing", async () => {
    apiGet.mockResolvedValue({ items: [], total: 0, next_cursor: null });
    render(<LedgerPanel customer={customer({ balance: "0.00" })} onChanged={() => undefined} />);
    expect(await screen.findByText("No credit sales or payments yet.")).toBeInTheDocument();
    expect(screen.queryByRole("form", { name: "Record a payment" })).not.toBeInTheDocument();
  });
});
