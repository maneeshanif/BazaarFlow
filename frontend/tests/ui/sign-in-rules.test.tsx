import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const login = vi.fn();
const replace = vi.fn();
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ login }) }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams(),
}));

import SignInPage from "@/app/(auth)/sign-in/page";
import { signInSchema } from "@/lib/validation/auth";

beforeEach(() => {
  login.mockReset();
  replace.mockReset();
});

describe("sign-in follows PRD F-001, one test per rule", () => {
  it("email: must be a valid address", () => {
    expect(signInSchema.safeParse({ email: "nope", password: "12345678" }).success).toBe(false);
    expect(signInSchema.safeParse({ email: "", password: "12345678" }).success).toBe(false);
    expect(signInSchema.safeParse({ email: "a@b.co", password: "12345678" }).success).toBe(true);
  });

  it("email: at most 254 characters", () => {
    const long = `${"a".repeat(64)}@${["b".repeat(63), "b".repeat(63), "b".repeat(63)].join(".")}.com`;
    expect(long.length).toBeGreaterThan(254);
    const result = signInSchema.safeParse({ email: long, password: "12345678" });
    expect(result.success).toBe(false);
  });

  it("password: at least 8 characters", () => {
    expect(signInSchema.safeParse({ email: "a@b.co", password: "1234567" }).success).toBe(false);
    expect(signInSchema.safeParse({ email: "a@b.co", password: "12345678" }).success).toBe(true);
  });

  it("shows the messages under the fields and sends nothing until the input is valid", async () => {
    render(<SignInPage />);
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Enter your email")).toBeInTheDocument();
    expect(screen.getByText("Password must be at least 8 characters")).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
  });

  it("only one request goes out for a double click", async () => {
    let finish: (v: { ok: true }) => void = () => undefined;
    login.mockReturnValue(new Promise((resolve) => (finish = resolve)));
    render(<SignInPage />);
    await userEvent.type(screen.getByLabelText(/^Email/), "owner@example.com");
    await userEvent.type(screen.getByLabelText(/^Password/), "12345678");
    await userEvent.dblClick(screen.getByRole("button", { name: "Sign in" }));
    expect(login).toHaveBeenCalledTimes(1);
    finish({ ok: true });
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });

  it("shop: asked only when the account belongs to several, and sent with the next attempt", async () => {
    login
      .mockResolvedValueOnce({
        ok: false,
        error: "Choose a shop to continue.",
        tenants: [
          { tenant_id: "t-a", tenant_name: "Shop A" },
          { tenant_id: "t-b", tenant_name: "Shop B" },
        ],
      })
      .mockResolvedValueOnce({ ok: true });
    render(<SignInPage />);
    expect(screen.queryByLabelText(/^Shop/)).not.toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/^Email/), "owner@example.com");
    await userEvent.type(screen.getByLabelText(/^Password/), "12345678");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    const shop = await screen.findByLabelText(/^Shop/);
    await userEvent.selectOptions(shop, "t-b");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(login).toHaveBeenLastCalledWith("owner@example.com", "12345678", "t-b"));
  });

  it("a locked account explains it in words", async () => {
    login.mockResolvedValue({ ok: false, error: "Too many failed attempts; try again later" });
    render(<SignInPage />);
    await userEvent.type(screen.getByLabelText(/^Email/), "owner@example.com");
    await userEvent.type(screen.getByLabelText(/^Password/), "12345678");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many failed attempts");
  });
});
