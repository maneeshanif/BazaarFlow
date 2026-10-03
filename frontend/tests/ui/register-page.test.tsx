import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const register = vi.fn();
const replace = vi.fn();
vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: () => ({ register }) }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));

import RegisterPage from "@/app/(auth)/register/page";
import { normalizePhone, registerSchema } from "@/lib/validation/register";

const valid = {
  full_name: "Ali Raza",
  email: "ali@example.com",
  password: "unusual-passphrase-42",
  shop_name: "Ali Mart",
  phone: "+923001234567",
  accept_terms: true,
};

beforeEach(() => {
  register.mockReset();
  replace.mockReset();
});

describe("F-002 rules in the form, one test per rule", () => {
  it("your name and shop name: 2 to 80 characters", () => {
    for (const field of ["full_name", "shop_name"] as const) {
      expect(registerSchema.safeParse({ ...valid, [field]: "A" }).success).toBe(false);
      expect(registerSchema.safeParse({ ...valid, [field]: " A " }).success).toBe(false);
      expect(registerSchema.safeParse({ ...valid, [field]: "x".repeat(81) }).success).toBe(false);
      expect(registerSchema.safeParse({ ...valid, [field]: "Al" }).success).toBe(true);
    }
  });

  it("email must look like an email", () => {
    expect(registerSchema.safeParse({ ...valid, email: "nope" }).success).toBe(false);
  });

  it("password needs 8 characters", () => {
    expect(registerSchema.safeParse({ ...valid, password: "Ab1!xyz" }).success).toBe(false);
  });

  it("phone: international format, with Pakistani numbers understood without a country code", () => {
    expect(normalizePhone("0300 1234567")).toBe("+923001234567");
    expect(normalizePhone("+92 300-1234567")).toBe("+923001234567");
    expect(normalizePhone("923001234567")).toBe("+923001234567");
    expect(normalizePhone("0044 20 7946 0958")).toBe("+442079460958");
    expect(registerSchema.safeParse({ ...valid, phone: "0300 1234567" }).success).toBe(true);
    expect(registerSchema.safeParse({ ...valid, phone: "123" }).success).toBe(false);
  });

  it("city is optional and at most 60 characters", () => {
    expect(registerSchema.safeParse({ ...valid, city: "" }).success).toBe(true);
    expect(registerSchema.safeParse({ ...valid, city: "c".repeat(61) }).success).toBe(false);
  });

  it("the terms must be accepted", () => {
    expect(registerSchema.safeParse({ ...valid, accept_terms: false }).success).toBe(false);
  });
});

async function fill(over: Partial<Record<string, string>> = {}) {
  const v = { name: "Ali Raza", shop: "Ali Mart", email: "ali@example.com", password: "unusual-passphrase-42", ...over };
  await userEvent.type(screen.getByLabelText(/^Your name/), v.name);
  await userEvent.type(screen.getByLabelText(/^Shop name/), v.shop);
  await userEvent.type(screen.getByLabelText(/^Email/), v.email);
  await userEvent.type(screen.getByLabelText(/^Password/), v.password);
  await userEvent.type(screen.getByLabelText(/^Phone/), "3001234567");
  await userEvent.click(screen.getByRole("checkbox"));
}

describe("the create-your-shop form", () => {
  it("starts with +92 in the phone field and explains every problem inline, sending nothing", async () => {
    render(<RegisterPage />);
    expect(screen.getByLabelText(/^Phone/)).toHaveValue("+92");
    await userEvent.click(screen.getByRole("button", { name: "Create shop" }));
    expect(await screen.findByText("Your name needs at least 2 characters")).toBeInTheDocument();
    expect(screen.getByText("Enter your email")).toBeInTheDocument();
    expect(screen.getByText("You need to accept the terms to create an account")).toBeInTheDocument();
    expect(register).not.toHaveBeenCalled();
  });

  it("creates the shop once for a double click and lands in the shop", async () => {
    let finish: (v: { ok: true }) => void = () => undefined;
    register.mockReturnValue(new Promise((resolve) => (finish = resolve)));
    render(<RegisterPage />);
    await fill();
    await userEvent.dblClick(screen.getByRole("button", { name: "Create shop" }));
    expect(register).toHaveBeenCalledTimes(1);
    expect(register.mock.calls[0][0]).toMatchObject({ email: "ali@example.com", phone: "+923001234567", accept_terms: true });
    finish({ ok: true });
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/inventory"));
  });

  it("shows the API's reasons under the right field", async () => {
    register.mockResolvedValue({
      ok: false,
      error: "password: is too common; choose something harder to guess",
      fieldErrors: { password: "is too common; choose something harder to guess" },
    });
    render(<RegisterPage />);
    await fill({ password: "password123" });
    await userEvent.click(screen.getByRole("button", { name: "Create shop" }));
    expect(await screen.findByText("is too common; choose something harder to guess")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Password/)).toHaveAttribute("aria-invalid", "true");
  });

  it("an existing email points to sign in", async () => {
    register.mockResolvedValue({ ok: false, error: "Email already registered", fieldErrors: {} });
    render(<RegisterPage />);
    await fill();
    await userEvent.click(screen.getByRole("button", { name: "Create shop" }));
    expect(await screen.findByText("That email already has an account. Sign in instead.")).toBeInTheDocument();
  });

  it("a sign-up limit or an outage is explained in a banner", async () => {
    register.mockResolvedValue({ ok: false, error: "Too many sign-ups from this connection. Try again later.", fieldErrors: {} });
    render(<RegisterPage />);
    await fill();
    await userEvent.click(screen.getByRole("button", { name: "Create shop" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many sign-ups");
  });
});
