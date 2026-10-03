import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/client";
import type { Dashboard } from "@/lib/api/types";

const apiGet = vi.fn();
vi.mock("@/lib/api/client", async (original) => ({
  ...(await original<typeof import("@/lib/api/client")>()),
  apiGet: (...a: unknown[]) => apiGet(...a),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }), usePathname: () => "/dashboard" }));

import DashboardPage from "@/app/(app)/(workspace)/dashboard/page";

const trend = (totals: number[]): Dashboard["trend"] =>
  totals.map((t, i) => ({ day: `2026-10-0${i + 1}`, total: t.toFixed(2), orders: t > 0 ? 1 : 0 }));

const owner = (over: Partial<Dashboard> = {}): Dashboard => ({
  role: "owner",
  range: "today",
  sales: { value: "2500.00", previous: "1000.00", change_percent: 150 },
  orders: { value: 2, previous: 1, change_percent: 100 },
  low_stock: 1,
  profit: { value: "800.00", previous: "400.00", change_percent: 100, orders_without_cost: 1 },
  unpaid_udhaar: "500.00",
  approvals_waiting: 1,
  briefing: "Today you made Rs 2,500 from 2 orders, up 150% on the period before.",
  trend: trend([0, 0, 0, 0, 0, 1000, 2500]),
  generated_at: "2026-10-07T10:00:00Z",
  ...over,
});

beforeEach(() => apiGet.mockReset());

describe("Home dashboard (PRD F-004, D-001)", () => {
  it("shows every figure for an owner, each linking to the records behind it", async () => {
    apiGet.mockResolvedValue(owner());
    render(<DashboardPage />);
    const figures = await screen.findByRole("region", { name: "Key figures" });
    const card = (label: RegExp) => within(figures).getByRole("link", { name: label });
    expect(card(/Today sales/)).toHaveTextContent("Rs 2,500");
    expect(card(/Today sales/)).toHaveTextContent("+150%");
    expect(card(/Today sales/)).toHaveAttribute("href", "/orders");
    expect(card(/Today profit/)).toHaveTextContent("Rs 800");
    expect(card(/Today orders/)).toHaveTextContent("2");
    expect(card(/Low-stock items/)).toHaveAttribute("href", "/inventory");
    expect(card(/Unpaid udhaar/)).toHaveTextContent("Rs 500");
    expect(card(/Unpaid udhaar/)).toHaveAttribute("href", "/customers");
    expect(card(/Approvals waiting/)).toHaveAttribute("href", "/approvals");
    expect(screen.getByRole("region", { name: "Briefing" })).toHaveTextContent("up 150% on the period before");
    expect(screen.getByText(/Profit leaves out 1 order with a product that has no cost/)).toBeInTheDocument();
  });

  it("a falling figure shows a minus and no comparison is shown when there is nothing to compare", async () => {
    apiGet.mockResolvedValue(owner({ sales: { value: "500.00", previous: "1000.00", change_percent: -50 }, orders: { value: 1, previous: 0, change_percent: null } }));
    render(<DashboardPage />);
    const figures = await screen.findByRole("region", { name: "Key figures" });
    expect(within(figures).getByRole("link", { name: /Today sales/ })).toHaveTextContent("-50%");
    expect(within(figures).getByRole("link", { name: /Today orders/ })).not.toHaveTextContent("%");
  });

  it("staff get only sales, orders and low stock, and no briefing", async () => {
    apiGet.mockResolvedValue(owner({ role: "staff", profit: null, unpaid_udhaar: null, approvals_waiting: null, briefing: null }));
    render(<DashboardPage />);
    const figures = await screen.findByRole("region", { name: "Key figures" });
    expect(within(figures).getAllByRole("link")).toHaveLength(3);
    expect(screen.queryByText(/profit/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Briefing" })).not.toBeInTheDocument();
  });

  it("changing the period asks the server again with that period", async () => {
    apiGet.mockResolvedValue(owner());
    render(<DashboardPage />);
    await screen.findByRole("region", { name: "Key figures" });
    apiGet.mockResolvedValue(owner({ range: "7d", sales: { value: "3500.00", previous: "0.00", change_percent: null } }));
    await userEvent.selectOptions(screen.getByLabelText("Period"), "7d");
    await waitFor(() => expect(apiGet).toHaveBeenLastCalledWith("/dashboard/summary", { range: "7d" }));
    expect(await screen.findByRole("link", { name: /Last 7 days sales/ })).toHaveTextContent("Rs 3,500");
  });

  it("the trend has a table for screen readers with every day", async () => {
    apiGet.mockResolvedValue(owner());
    render(<DashboardPage />);
    const table = await screen.findByRole("table", { name: "Sales per day, last 7 days" });
    expect(within(table).getAllByRole("row")).toHaveLength(8);
    expect(within(table).getByRole("row", { name: /2026-10-07/ })).toHaveTextContent("Rs 2,500");
  });

  it("with no sales it says what to do instead of showing an empty chart", async () => {
    apiGet.mockResolvedValue(owner({ trend: trend([0, 0, 0, 0, 0, 0, 0]), sales: { value: "0.00", previous: "0.00", change_percent: null }, orders: { value: 0, previous: 0, change_percent: null } }));
    render(<DashboardPage />);
    expect(await screen.findByText(/No sales in the last 7 days/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "New sale" })).toHaveAttribute("href", "/sales/new");
  });

  it("shows a skeleton while loading and an error with a working retry", async () => {
    let finish: (d: Dashboard) => void = () => undefined;
    apiGet.mockReturnValueOnce(new Promise<Dashboard>((resolve) => (finish = resolve)));
    const first = render(<DashboardPage />);
    expect(screen.getByRole("status", { name: "Loading the dashboard" })).toBeInTheDocument();
    finish(owner());
    await screen.findByRole("region", { name: "Key figures" });
    first.unmount();

    apiGet.mockRejectedValueOnce(new ApiError(500, "The server is busy.")).mockResolvedValueOnce(owner());
    render(<DashboardPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The server is busy.");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("region", { name: "Key figures" })).toBeInTheDocument();
  });
});
