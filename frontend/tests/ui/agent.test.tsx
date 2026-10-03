import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/client";
import type { AgentRun, AgentRunDetail, AgentStatus, Approval, ChatResponse } from "@/lib/api/types";

const apiGet = vi.fn();
const apiPost = vi.fn();
const apiPut = vi.fn();
const apiPatch = vi.fn();
vi.mock("@/lib/api/client", async (original) => ({
  ...(await original<typeof import("@/lib/api/client")>()),
  apiGet: (...a: unknown[]) => apiGet(...a),
  apiPost: (...a: unknown[]) => apiPost(...a),
  apiPut: (...a: unknown[]) => apiPut(...a),
  apiPatch: (...a: unknown[]) => apiPatch(...a),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/approvals",
  useParams: () => ({ id: "run-1" }),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
let role: "owner" | "manager" | "staff" = "manager";
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ role, status: "authenticated" }) }));

import AgentActivityPage from "@/app/(app)/(workspace)/agent-activity/page";
import AgentRunPage from "@/app/(app)/(workspace)/agent-activity/[id]/page";
import ApprovalsPage from "@/app/(app)/(workspace)/approvals/page";
import { ChatPanel } from "@/components/agent/ChatPanel";

const approval = (over: Partial<Approval> = {}): Approval => ({
  id: "a1",
  agent: "sales",
  tool: "post_order",
  summary: "Post a sale of Rs 5,000.00 (1 item line, cash)",
  details: ["2 x Classic Shirt", "Customer: Ali Raza", "Total Rs 5,000.00; paid now Rs 5,000.00 by cash; on credit Rs 0.00"],
  payload: { items: [{ product_id: "p1", qty: 2, unit_price: null }], payment_method: "cash" },
  status: "pending",
  requested_by: "u1",
  requested_by_name: "Sana Staff",
  decided_by: null,
  decision_note: null,
  created_at: "2026-10-03T10:00:00Z",
  expires_at: "2026-10-04T10:00:00Z",
  executed_at: null,
  ...over,
});

const reply = (over: Partial<ChatResponse> = {}): ChatResponse => ({ reply: "Draft sale. Post it?", session_id: "sess1", outcome: "ok", run_id: "r1", actions: [], notice: null, ...over });

beforeEach(() => {
  [apiGet, apiPost, apiPut, apiPatch].forEach((m) => m.mockReset());
  role = "manager";
  Element.prototype.scrollIntoView = vi.fn();
});

describe("Sales chat (PRD F-006)", () => {
  it("starts with an explanation and examples in English and Roman Urdu, and an example fills the box", async () => {
    render(<ChatPanel />);
    expect(screen.getByText("Tell me what you sold")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "2 shirt bech do Ali ko" }));
    expect(screen.getByLabelText("Your message")).toHaveValue("2 shirt bech do Ali ko");
  });

  it("sends once for a double Enter, shows the reply, and keeps the same session", async () => {
    let finish: (r: ChatResponse) => void = () => undefined;
    apiPost.mockReturnValueOnce(new Promise<ChatResponse>((resolve) => (finish = resolve))).mockResolvedValueOnce(reply({ reply: "Sent for approval." }));
    render(<ChatPanel />);
    const box = screen.getByLabelText("Your message");
    await userEvent.type(box, "sell 2 shirt to ali{Enter}");
    expect(apiPost).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("Thinking...")).toBeInTheDocument();
    finish(reply());
    expect(await screen.findByText("Draft sale. Post it?")).toBeInTheDocument();
    await userEvent.type(box, "yes{Enter}");
    await waitFor(() => expect(apiPost).toHaveBeenCalledTimes(2));
    expect(apiPost).toHaveBeenLastCalledWith("/chat/sales", { message: "yes", session_id: "sess1" });
  });

  it("a manager approves a proposal right in the conversation", async () => {
    apiPost
      .mockResolvedValueOnce(reply({ reply: "Sent for approval.", actions: [{ id: "a1", tool: "post_order", summary: approval().summary, status: "pending" }] }))
      .mockResolvedValueOnce(approval({ status: "executed", executed_at: "2026-10-03T10:05:00Z" }));
    apiGet.mockResolvedValue(approval());
    render(<ChatPanel />);
    await userEvent.type(screen.getByLabelText("Your message"), "yes{Enter}");
    const card = await screen.findByRole("article", { name: /Sale: Post a sale/ });
    expect(within(card).getByText("2 x Classic Shirt")).toBeInTheDocument();
    await userEvent.click(within(card).getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(apiPost).toHaveBeenLastCalledWith("/approvals/a1/approve"));
    expect(await within(card).findByText("executed")).toBeInTheDocument();
    expect(within(card).queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

  it("staff see that a manager must approve, with no buttons and no approvals request", async () => {
    role = "staff";
    apiPost.mockResolvedValue(reply({ reply: "Sent for approval.", actions: [{ id: "a1", tool: "post_order", summary: approval().summary, status: "pending" }] }));
    render(<ChatPanel />);
    await userEvent.type(screen.getByLabelText("Your message"), "yes{Enter}");
    expect(await screen.findByText(/Waiting for a manager or the owner to approve it/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(apiGet).not.toHaveBeenCalled();
  });

  it("a failure and a paused assistant are explained in words", async () => {
    apiPost.mockRejectedValueOnce(new ApiError(0, "Could not reach the server. Check your connection and try again.", "network")).mockResolvedValueOnce(reply({ reply: "The AI assistant is paused for this shop.", outcome: "paused" }));
    render(<ChatPanel />);
    await userEvent.type(screen.getByLabelText("Your message"), "hello{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not reach the server");
    await userEvent.type(screen.getByLabelText("Your message"), "hello again{Enter}");
    expect(await screen.findByText("The AI assistant is paused for this shop.")).toBeInTheDocument();
  });
});

describe("Approvals center (PRD F-021)", () => {
  it("lists what is waiting with plain-words details, and the other filters have their own empty messages", async () => {
    apiGet.mockResolvedValue({ items: [approval()], total: 1, next_cursor: null });
    render(<ApprovalsPage />);
    expect(await screen.findByText("Customer: Ali Raza")).toBeInTheDocument();
    expect(screen.getByText(/Asked .* by Sana Staff/)).toBeInTheDocument();
    apiGet.mockResolvedValue({ items: [], total: 0, next_cursor: null });
    await userEvent.selectOptions(screen.getByLabelText("Show"), "rejected");
    expect(await screen.findByText("Nothing has been rejected.")).toBeInTheDocument();
    expect(apiGet).toHaveBeenLastCalledWith("/approvals/", expect.objectContaining({ status: "rejected" }));
  });

  it("approving is one request even for a double click, and a run the rules now refuse explains why", async () => {
    apiGet.mockResolvedValue({ items: [approval()], total: 1, next_cursor: null });
    apiPost.mockResolvedValueOnce(approval({ status: "failed", decision_note: "execution failed: Not enough stock" }));
    render(<ApprovalsPage />);
    await userEvent.dblClick(await screen.findByRole("button", { name: "Approve" }));
    await waitFor(() => expect(apiPost).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("execution failed: Not enough stock")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

  it("rejecting needs a reason, then records it once", async () => {
    apiGet.mockResolvedValue({ items: [approval({ id: "a2" })], total: 1, next_cursor: null });
    apiPost.mockResolvedValue(approval({ id: "a2", status: "rejected", decision_note: "Wrong customer" }));
    render(<ApprovalsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Reject" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Reject" }));
    expect(await within(dialog).findByText("Give a reason of at least 3 characters")).toBeInTheDocument();
    expect(apiPost).not.toHaveBeenCalled();
    await userEvent.type(within(dialog).getByLabelText(/^Why are you rejecting it/), "Wrong customer");
    await userEvent.dblClick(within(dialog).getByRole("button", { name: "Reject" }));
    await waitFor(() => expect(apiPost).toHaveBeenCalledTimes(1));
    expect(apiPost).toHaveBeenCalledWith("/approvals/a2/reject", { reason: "Wrong customer" });
    expect(await screen.findByText("Wrong customer")).toBeInTheDocument();
  });

  it("editing a sale changes its quantities and sends the whole payload back", async () => {
    apiGet.mockResolvedValue({ items: [approval()], total: 1, next_cursor: null });
    apiPatch.mockResolvedValue(approval({ payload: { items: [{ product_id: "p1", qty: 1, unit_price: null }], payment_method: "cash" } }));
    render(<ApprovalsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit" }));
    const qty = await screen.findByLabelText(/^Quantity: 2 x Classic Shirt/);
    await userEvent.clear(qty);
    await userEvent.type(qty, "0");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText(/whole number above zero/)).toBeInTheDocument();
    expect(apiPatch).not.toHaveBeenCalled();
    await userEvent.clear(qty);
    await userEvent.type(qty, "1");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(apiPatch).toHaveBeenCalledWith("/approvals/a1", { payload: { items: [{ product_id: "p1", qty: 1, unit_price: null }], payment_method: "cash" } }));
  });

  it("is restricted for staff and has loading, error and retry states", async () => {
    role = "staff";
    const restricted = render(<ApprovalsPage />);
    expect(await screen.findByText("Access is restricted")).toBeInTheDocument();
    restricted.unmount();
    role = "manager";
    apiGet.mockRejectedValueOnce(new ApiError(500, "The server is busy.")).mockResolvedValueOnce({ items: [approval()], total: 1, next_cursor: null });
    render(<ApprovalsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The server is busy.");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Customer: Ali Raza")).toBeInTheDocument();
  });
});

const run = (over: Partial<AgentRun> = {}): AgentRun => ({
  id: "run-1",
  user_id: "u1",
  user_name: "Sana Staff",
  agent: "sales",
  session_id: "sess1",
  outcome: "ok",
  input_text: "sell 2 shirt to [customer]",
  output_text: "Draft sale. Post it?",
  tokens_in: 240,
  tokens_out: 80,
  spend_usd: "0.0001",
  duration_ms: 420,
  action_ids: [],
  created_at: "2026-10-03T10:00:00Z",
  ...over,
});
const status = (over: Partial<AgentStatus> = {}): AgentStatus => ({ enabled: true, month_spend_usd: "0.04", month_cap_usd: "5.00", percent_used: 1, runs_this_month: 3, ...over });

describe("Agent activity (PRD F-022)", () => {
  it("shows the allowance and every run, and only the owner can pause the assistant", async () => {
    apiGet.mockImplementation((path: string) => Promise.resolve(path === "/agent-runs/status" ? status() : { items: [run()], total: 1, next_cursor: null }));
    const asManager = render(<AgentActivityPage />);
    expect(await screen.findByText("$0.04 of $5.00 used (1%)")).toBeInTheDocument();
    expect(screen.getByText("Sana Staff")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pause the assistant" })).not.toBeInTheDocument();
    asManager.unmount();

    role = "owner";
    apiPut.mockResolvedValue(status({ enabled: false }));
    render(<AgentActivityPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Pause the assistant" }));
    await waitFor(() => expect(apiPut).toHaveBeenCalledWith("/agent-runs/switch", { enabled: false }));
    expect(await screen.findByRole("button", { name: "Switch it on" })).toBeInTheDocument();
    expect(screen.getByText(/Paused. Nobody can use it/)).toBeInTheDocument();
  });

  it("warns near the limit and filters by result", async () => {
    apiGet.mockImplementation((path: string) => Promise.resolve(path === "/agent-runs/status" ? status({ percent_used: 85 }) : { items: [run({ outcome: "spend_limit" })], total: 1, next_cursor: null }));
    render(<AgentActivityPage />);
    expect(await screen.findByText("More than 80% of the allowance is used.")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Result"), "failed");
    await waitFor(() => expect(apiGet).toHaveBeenLastCalledWith("/agent-runs/", expect.objectContaining({ outcome: "failed" })));
  });

  it("the detail page shows the redacted conversation and each tool the agent called", async () => {
    const detail: AgentRunDetail = {
      ...run({ action_ids: ["a1"] }),
      trace: [{ tool: "find_product", arguments: { query: "shirt" }, result: "id=p1 | Classic Shirt", ok: true }, { tool: "record_payment", arguments: {}, result: "Not allowed", ok: false }],
    };
    apiGet.mockResolvedValue(detail);
    render(<AgentRunPage />);
    expect(await screen.findByText("sell 2 shirt to [customer]")).toBeInTheDocument();
    expect(screen.getByText("find_product")).toBeInTheDocument();
    expect(screen.getByText("Not allowed")).toBeInTheDocument();
    expect(screen.getByText(/hidden in this record on purpose/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Approvals" })).toHaveAttribute("href", "/approvals");
  });
});
