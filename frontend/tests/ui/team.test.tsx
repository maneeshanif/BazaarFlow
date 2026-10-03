import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/client";
import type { TeamMember } from "@/lib/api/types";

const apiGet = vi.fn();
const apiPatch = vi.fn();
const apiPost = vi.fn();
const apiDelete = vi.fn();
const push = vi.fn();
vi.mock("@/lib/api/client", async (original) => ({
  ...(await original<typeof import("@/lib/api/client")>()),
  apiGet: (...a: unknown[]) => apiGet(...a),
  apiPatch: (...a: unknown[]) => apiPatch(...a),
  apiPost: (...a: unknown[]) => apiPost(...a),
  apiDelete: (...a: unknown[]) => apiDelete(...a),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn() }), usePathname: () => "/team" }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
let role: "owner" | "manager" = "owner";
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ role, status: "authenticated" }) }));

import TeamPage from "@/app/(app)/(workspace)/team/page";
import { TeamMemberForm } from "@/components/team/TeamMemberForm";

const person = (over: Partial<TeamMember> = {}): TeamMember => ({
  id: "m1",
  user_id: "u1",
  name: "Sana Staff",
  email: "sana@example.com",
  role: "staff",
  is_active: true,
  joined_at: "2026-10-01T10:00:00Z",
  is_you: false,
  new_account: false,
  ...over,
});
const owner = person({ id: "m0", user_id: "u0", name: "Ali Owner", email: "ali@example.com", role: "owner", is_you: true });

beforeEach(() => {
  [apiGet, apiPatch, apiPost, apiDelete, push].forEach((m) => m.mockReset());
  role = "owner";
});

describe("Team list (PRD F-019)", () => {
  it("shows the owner without a role control, and a role control for everyone else", async () => {
    apiGet.mockResolvedValue([owner, person()]);
    render(<TeamPage />);
    const table = await screen.findByRole("table", { name: "Team" });
    expect(within(table).getByText("(you)")).toBeInTheDocument();
    expect(within(table).getByLabelText("Role of Sana Staff")).toHaveValue("staff");
    expect(within(table).queryByLabelText("Role of Ali Owner")).not.toBeInTheDocument();
    expect(within(table).queryByRole("button", { name: "Remove Ali Owner" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add team member" })).toHaveAttribute("href", "/team/new");
    expect(screen.getByText("What each role can do")).toBeInTheDocument();
  });

  it("changing a role goes to the API and the list is reloaded", async () => {
    apiGet.mockResolvedValue([owner, person()]);
    apiPatch.mockResolvedValue(person({ role: "manager" }));
    render(<TeamPage />);
    await userEvent.selectOptions(await screen.findByLabelText("Role of Sana Staff"), "manager");
    await waitFor(() => expect(apiPatch).toHaveBeenCalledWith("/team/m1", { role: "manager" }));
    await waitFor(() => expect(apiGet).toHaveBeenCalledTimes(2));
  });

  it("removing asks first, names the person, and removes once", async () => {
    apiGet.mockResolvedValue([owner, person()]);
    apiDelete.mockResolvedValue(undefined);
    render(<TeamPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Remove Sana Staff" }));
    expect(await screen.findByText("Remove Sana Staff?")).toBeInTheDocument();
    expect(apiDelete).not.toHaveBeenCalled();
    await userEvent.dblClick(screen.getByRole("button", { name: "Remove from team" }));
    await waitFor(() => expect(apiDelete).toHaveBeenCalledTimes(1));
    expect(apiDelete).toHaveBeenCalledWith("/team/m1");
  });

  it("a manager is told the page is restricted; loading, empty and error states are shown", async () => {
    role = "manager";
    apiGet.mockResolvedValue([owner]);
    const restricted = render(<TeamPage />);
    expect(await screen.findByText("Access is restricted")).toBeInTheDocument();
    expect(apiGet).not.toHaveBeenCalled();
    restricted.unmount();

    role = "owner";
    apiGet.mockReturnValue(new Promise(() => undefined));
    const loading = render(<TeamPage />);
    expect(screen.getAllByTestId("skeleton-row").length).toBeGreaterThan(0);
    loading.unmount();

    apiGet.mockRejectedValueOnce(new ApiError(500, "The server is busy.")).mockResolvedValueOnce([owner]);
    render(<TeamPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The server is busy.");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Ali Owner")).toBeInTheDocument();
  });
});

describe("Add team member form", () => {
  async function fill() {
    await userEvent.type(screen.getByLabelText(/^Name/), "Sana Staff");
    await userEvent.type(screen.getByLabelText(/^Email/), "sana@example.com");
  }

  it("explains what each role can do and checks the input before sending", async () => {
    render(<TeamMemberForm />);
    expect(screen.getByText(/Records sales and customers/)).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText(/^Role/), "manager");
    expect(screen.getByText(/Runs the day/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Add to team" }));
    expect(await screen.findByText("Name needs at least 2 characters")).toBeInTheDocument();
    expect(screen.getByText("Enter their email")).toBeInTheDocument();
    expect(apiPost).not.toHaveBeenCalled();
  });

  it("refuses a short first password before the server is asked", async () => {
    render(<TeamMemberForm />);
    await fill();
    await userEvent.type(screen.getByLabelText(/^First password/), "short");
    await userEvent.click(screen.getByRole("button", { name: "Add to team" }));
    expect(await screen.findByText("Password must be at least 8 characters")).toBeInTheDocument();
    expect(apiPost).not.toHaveBeenCalled();
  });

  it("adds once for a double click and returns to the team", async () => {
    apiPost.mockResolvedValue(person({ new_account: true }));
    render(<TeamMemberForm />);
    await fill();
    await userEvent.type(screen.getByLabelText(/^First password/), "first-pass-2026");
    await userEvent.dblClick(screen.getByRole("button", { name: "Add to team" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/team"));
    expect(apiPost).toHaveBeenCalledTimes(1);
    expect(apiPost).toHaveBeenCalledWith("/team/", { name: "Sana Staff", email: "sana@example.com", role: "staff", password: "first-pass-2026" });
  });

  it("puts the server's reasons under the right field", async () => {
    apiPost.mockRejectedValue(new ApiError(422, "Give them a first password. They can sign in with it straight away.", "password_required"));
    render(<TeamMemberForm />);
    await fill();
    await userEvent.click(screen.getByRole("button", { name: "Add to team" }));
    expect(await screen.findByText(/Give them a first password/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^First password/)).toHaveAttribute("aria-invalid", "true");
  });
});
