import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import SignInPage from "@/app/(marketing)/sign-in/page";

const replace = vi.fn();
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams(search),
}));

const login = vi.fn();
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ login }) }));

beforeEach(() => {
  replace.mockReset();
  login.mockReset();
  search = "";
});

async function fill() {
  await userEvent.type(screen.getByLabelText(/email/i), "ali@example.com");
  await userEvent.type(screen.getByLabelText(/password/i), "correct-horse");
}

describe("sign-in page", () => {
  it("signs in and goes to the dashboard", async () => {
    login.mockResolvedValue({ ok: true });
    render(<SignInPage />);
    await fill();
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(login).toHaveBeenCalledWith("ali@example.com", "correct-horse", undefined);
  });

  it("returns to the page the visitor was trying to open", async () => {
    search = "next=%2Fdashboard%2Forders";
    login.mockResolvedValue({ ok: true });
    render(<SignInPage />);
    await fill();
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard/orders"));
  });

  it("ignores an off-site next parameter", async () => {
    search = "next=https%3A%2F%2Fevil.example";
    login.mockResolvedValue({ ok: true });
    render(<SignInPage />);
    await fill();
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });

  it("shows a wrong password as an alert and stays on the page", async () => {
    login.mockResolvedValue({ ok: false, error: "Invalid email or password" });
    render(<SignInPage />);
    await fill();
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
    expect(replace).not.toHaveBeenCalled();
  });

  it("asks which shop to open when the account belongs to several", async () => {
    login.mockResolvedValueOnce({
      ok: false,
      error: "Choose a shop to continue.",
      tenants: [
        { tenant_id: "t-a", tenant_name: "Ali Mart" },
        { tenant_id: "t-b", tenant_name: "Sara Boutique" },
      ],
    });
    login.mockResolvedValueOnce({ ok: true });
    render(<SignInPage />);
    await fill();
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await userEvent.selectOptions(await screen.findByLabelText(/shop/i), "t-b");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(login).toHaveBeenLastCalledWith("ali@example.com", "correct-horse", "t-b");
  });
});
