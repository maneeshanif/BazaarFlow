import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CommentReply, PurchaseOrder } from "@/lib/api/types";

const apiGet = vi.fn();
const apiPost = vi.fn();
vi.mock("@/lib/api/client", async (original) => ({
  ...(await original<typeof import("@/lib/api/client")>()),
  apiGet: (...a: unknown[]) => apiGet(...a),
  apiPost: (...a: unknown[]) => apiPost(...a),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

import { CommentsView } from "@/components/marketing/CommentsView";
import { PurchaseOrdersView } from "@/components/purchasing/PurchaseOrdersView";

const order = (over: Partial<PurchaseOrder> = {}): PurchaseOrder => ({
  id: "o1",
  vendor_id: "v1",
  vendor_name: "Cloth House",
  vendor_has_phone: true,
  status: "drafted",
  total: "780.00",
  item_count: 2,
  action_id: "a1",
  created_at: "2026-10-13T09:00:00Z",
  sent_at: null,
  ...over,
});

const reply = (over: Partial<CommentReply> = {}): CommentReply => ({
  id: "r1",
  post_id: "p1",
  post_title: "Eid sale",
  author: "Sara",
  comment_text: "What is the price?",
  reply_text: "Thank you! Please message us on WhatsApp.",
  status: "proposed",
  action_id: "a1",
  last_error: null,
  created_at: "2026-10-13T09:00:00Z",
  posted_at: null,
  ...over,
});

const page = <T,>(items: T[]) => ({ items, total: items.length, next_cursor: null });

beforeEach(() => {
  apiGet.mockReset();
  apiPost.mockReset();
});

describe("Purchase orders (PRD W-006)", () => {
  it("lists the drafts with vendor, items and the estimated total", async () => {
    apiGet.mockResolvedValue(page([order()]));
    render(<PurchaseOrdersView />);
    expect(await screen.findByText("Cloth House")).toBeInTheDocument();
    expect(screen.getByText("Rs 780")).toBeInTheDocument();
    expect(apiGet).toHaveBeenCalledWith("/purchase-orders/", expect.objectContaining({ limit: 25 }));
  });

  it("cancels a draft once, even on a double click, and reloads the list", async () => {
    apiGet.mockResolvedValue(page([order()]));
    let finish: (value: unknown) => void = () => undefined;
    apiPost.mockImplementation(() => new Promise((resolve) => (finish = resolve))); // the request is still running
    render(<PurchaseOrdersView />);
    await userEvent.dblClick(await screen.findByRole("button", { name: "Cancel" }));
    expect(apiPost).toHaveBeenCalledTimes(1);
    expect(apiPost).toHaveBeenCalledWith("/purchase-orders/o1/cancel");
    finish({ ...order({ status: "cancelled" }), items: [], note: null });
    await waitFor(() => expect(apiGet.mock.calls.length).toBeGreaterThan(1)); // the list reloads once it is done
  });

  it("offers no cancel for an order that was already sent, and explains a vendor with no phone", async () => {
    apiGet.mockResolvedValue(page([order({ status: "sent", sent_at: "2026-10-13T10:00:00Z" }), order({ id: "o2", status: "drafted", vendor_has_phone: false })]));
    render(<PurchaseOrdersView />);
    await screen.findAllByText("Cloth House");
    expect(screen.getAllByRole("button", { name: "Cancel" })).toHaveLength(1);
    expect(screen.getByText(/No phone number for this vendor/)).toBeInTheDocument();
  });

  it("shows the empty state in words", async () => {
    apiGet.mockResolvedValue(page([]));
    render(<PurchaseOrdersView />);
    expect(await screen.findByText(/No purchase orders yet/)).toBeInTheDocument();
  });

  it("shows an error with a retry", async () => {
    apiGet.mockRejectedValueOnce(new Error("boom"));
    apiGet.mockResolvedValueOnce(page([order()]));
    render(<PurchaseOrdersView />);
    await userEvent.click(await screen.findByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Cloth House")).toBeInTheDocument();
  });
});

describe("Facebook comments (PRD W-004)", () => {
  it("shows the comment as plain text next to the proposed reply, with a Skip for a waiting one", async () => {
    apiGet.mockResolvedValue(page([reply({ comment_text: "<b>Hello</b>" }), reply({ id: "r2", status: "posted", posted_at: "2026-10-13T10:00:00Z" })]));
    render(<CommentsView />);
    expect(await screen.findByText("<b>Hello</b>")).toBeInTheDocument(); // markup in a comment is text, never rendered
    expect(screen.getAllByRole("button", { name: "Skip" })).toHaveLength(1);
    expect(apiGet).toHaveBeenCalledWith("/marketing/comments/", expect.objectContaining({ limit: 25 }));
  });

  it("skips a reply and reloads", async () => {
    apiGet.mockResolvedValue(page([reply()]));
    apiPost.mockResolvedValue(reply({ status: "skipped" }));
    render(<CommentsView />);
    await userEvent.click(await screen.findByRole("button", { name: "Skip" }));
    await waitFor(() => expect(apiPost).toHaveBeenCalledWith("/marketing/comments/r1/skip"));
    await waitFor(() => expect(apiGet.mock.calls.length).toBeGreaterThan(1));
  });
});
