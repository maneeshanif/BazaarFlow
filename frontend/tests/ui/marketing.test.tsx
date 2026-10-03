import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/client";
import type { MarketingPost } from "@/lib/api/types";

const apiGet = vi.fn();
const apiPost = vi.fn();
const apiPatch = vi.fn();
const apiDelete = vi.fn();
const push = vi.fn();
vi.mock("@/lib/api/client", async (original) => ({
  ...(await original<typeof import("@/lib/api/client")>()),
  apiGet: (...a: unknown[]) => apiGet(...a),
  apiPost: (...a: unknown[]) => apiPost(...a),
  apiPatch: (...a: unknown[]) => apiPatch(...a),
  apiDelete: (...a: unknown[]) => apiDelete(...a),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
  usePathname: () => "/marketing",
  useParams: () => ({ id: "p1" }),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
let role: "owner" | "manager" | "staff" = "manager";
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ role, status: "authenticated" }) }));

import MarketingPostPage from "@/app/(app)/(workspace)/marketing/[id]/page";
import MarketingStudioPage from "@/app/(app)/(workspace)/marketing/page";
import { DraftBriefForm } from "@/components/marketing/DraftBriefForm";
import { PostEditor } from "@/components/marketing/PostEditor";

const post = (over: Partial<MarketingPost> = {}): MarketingPost => ({
  id: "p1",
  title: "Eid sale at Ali Store",
  message: "Come and see our new shirts today!",
  hashtags: "#eid #sale",
  status: "draft",
  created_at: "2026-10-03T10:00:00Z",
  updated_at: "2026-10-03T10:00:00Z",
  ...over,
});

beforeEach(() => {
  [apiGet, apiPost, apiPatch, apiDelete, push].forEach((m) => m.mockReset());
  role = "manager";
});

describe("Draft a post (PRD F-014)", () => {
  it("promoting a product needs a product, and the product comes from a search dialog", async () => {
    apiGet.mockResolvedValue({ items: [{ id: "pr1", name: "Classic Shirt", sku: "SHIRT" }], total: 1, next_cursor: null });
    render(<DraftBriefForm />);
    await userEvent.selectOptions(screen.getByLabelText(/What is the post for/), "promote_product");
    await userEvent.click(screen.getByRole("button", { name: "Write the draft" }));
    expect(await screen.findByText("Choose the product to promote")).toBeInTheDocument();
    expect(apiPost).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: /Product: none chosen/ }));
    await userEvent.click(await screen.findByRole("button", { name: /Classic Shirt/ }));
    expect(screen.getByRole("button", { name: /Product: Classic Shirt\. Change/ })).toBeInTheDocument();
    expect(screen.queryByText("Choose the product to promote")).not.toBeInTheDocument();
  });

  it("writes one draft for a double click and opens it", async () => {
    apiPost.mockResolvedValue(post());
    render(<DraftBriefForm />);
    await userEvent.selectOptions(screen.getByLabelText(/^Language/), "roman_urdu");
    await userEvent.type(screen.getByLabelText(/Anything it should mention/), "  20% off this week ");
    await userEvent.dblClick(screen.getByRole("button", { name: "Write the draft" }));
    await waitFor(() => expect(apiPost).toHaveBeenCalledTimes(1));
    expect(apiPost).toHaveBeenCalledWith("/marketing/posts/drafts", { goal: "general", tone: "friendly", language: "roman_urdu", notes: "20% off this week" });
    await waitFor(() => expect(push).toHaveBeenCalledWith("/marketing/p1"));
  });

  it("explains a paused assistant in words and lets you try again", async () => {
    apiPost.mockRejectedValueOnce(new ApiError(409, "The AI assistant is paused for this shop. The owner can switch it on in Agent activity.", "agents_paused"));
    render(<DraftBriefForm />);
    await userEvent.click(screen.getByRole("button", { name: "Write the draft" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("paused for this shop");
    expect(push).not.toHaveBeenCalled();
    apiPost.mockResolvedValueOnce(post());
    await userEvent.click(screen.getByRole("button", { name: "Write the draft" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/marketing/p1"));
  });
});

describe("Edit a post (PRD F-014)", () => {
  it.each([
    ["Title", "", "Give the post a title"],
    ["Message", "", "Write the message"],
    ["Hashtags", "#bad-tag", "Hashtags use letters, numbers and underscores only"],
  ])("%s rule: %j shows %s and nothing is saved", async (label, value, message) => {
    render(<PostEditor post={post()} />);
    const field = screen.getByLabelText(new RegExp(`^${label}`));
    await userEvent.clear(field);
    if (value) await userEvent.type(field, value);
    await userEvent.tab();
    expect(await screen.findByText(message)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(apiPatch).not.toHaveBeenCalled();
  });

  it("saves with tidy hashtags, shows the saved version, then sends it for approval", async () => {
    apiPatch.mockResolvedValue(post({ title: "Eid sale", hashtags: "#eid #sale" }));
    apiPost.mockResolvedValue(post({ title: "Eid sale", status: "pending_approval" }));
    render(<PostEditor post={post()} />);
    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled();
    const title = screen.getByLabelText(/^Title/);
    await userEvent.clear(title);
    await userEvent.type(title, "Eid sale");
    const tags = screen.getByLabelText(/^Hashtags/);
    await userEvent.clear(tags);
    await userEvent.type(tags, "eid  sale");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() =>
      expect(apiPatch).toHaveBeenCalledWith("/marketing/posts/p1", { title: "Eid sale", message: "Come and see our new shirts today!", hashtags: "#eid #sale" }),
    );
    await userEvent.dblClick(screen.getByRole("button", { name: "Send for approval" }));
    await waitFor(() => expect(apiPost).toHaveBeenCalledTimes(1));
    expect(apiPost).toHaveBeenCalledWith("/marketing/posts/p1/submit");
    expect(await screen.findByText(/Waiting for a manager or the owner/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Send for approval" })).not.toBeInTheDocument();
    expect(screen.getByLabelText(/^Message/)).toHaveAttribute("readonly");
  });

  it("sending with unsaved changes saves them first", async () => {
    apiPatch.mockResolvedValue(post({ message: "Fresh words" }));
    apiPost.mockResolvedValue(post({ message: "Fresh words", status: "pending_approval" }));
    render(<PostEditor post={post()} />);
    const message = screen.getByLabelText(/^Message/);
    await userEvent.clear(message);
    await userEvent.type(message, "Fresh words");
    await userEvent.click(screen.getByRole("button", { name: "Send for approval" }));
    await waitFor(() => expect(apiPost).toHaveBeenCalledTimes(1));
    expect(apiPatch).toHaveBeenCalledTimes(1);
  });

  it("an approved post is read-only and says publishing comes later", () => {
    render(<PostEditor post={post({ status: "approved" })} />);
    expect(screen.getByText(/Publishing to Facebook arrives in a later update/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save changes" })).not.toBeInTheDocument();
    expect(screen.getByLabelText(/^Title/)).toHaveAttribute("readonly");
  });

  it("removing a draft asks first, names it, and goes back to the studio", async () => {
    apiDelete.mockResolvedValue(undefined);
    render(<PostEditor post={post()} />);
    await userEvent.click(screen.getByRole("button", { name: "Remove draft" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText('Remove "Eid sale at Ali Store"?')).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Remove draft" }));
    await waitFor(() => expect(apiDelete).toHaveBeenCalledWith("/marketing/posts/p1"));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/marketing"));
  });
});

describe("Studio pages", () => {
  it("lists posts with their status, filters, and has an empty message that says what to do", async () => {
    apiGet.mockResolvedValue({ items: [post(), post({ id: "p2", title: "Festival greeting", status: "approved" })], total: 2, next_cursor: null });
    render(<MarketingStudioPage />);
    expect(await screen.findByRole("link", { name: "Eid sale at Ali Store" })).toHaveAttribute("href", "/marketing/p1");
    expect(screen.getByText("approved")).toBeInTheDocument();
    apiGet.mockResolvedValue({ items: [], total: 0, next_cursor: null });
    await userEvent.selectOptions(screen.getByLabelText("Show"), "pending_approval");
    expect(await screen.findByText("No posts have this status.")).toBeInTheDocument();
    expect(apiGet).toHaveBeenLastCalledWith("/marketing/posts/", expect.objectContaining({ status: "pending_approval" }));
  });

  it("staff are told access is restricted", async () => {
    role = "staff";
    render(<MarketingStudioPage />);
    expect(await screen.findByText("Access is restricted")).toBeInTheDocument();
  });

  it("the post page shows loading, a missing post, and the editor", async () => {
    apiGet.mockRejectedValueOnce(new ApiError(404, "That post does not exist"));
    const missing = render(<MarketingPostPage />);
    expect(await screen.findByText("That post does not exist.")).toBeInTheDocument();
    missing.unmount();
    apiGet.mockResolvedValue(post());
    render(<MarketingPostPage />);
    expect(await screen.findByRole("form", { name: "Post" })).toBeInTheDocument();
    expect(screen.getByLabelText(/^Title/)).toHaveValue("Eid sale at Ali Store");
  });
});
