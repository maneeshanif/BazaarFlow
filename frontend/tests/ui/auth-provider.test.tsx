import { act, render, screen, waitFor } from "@testing-library/react";
import axios from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RequireRole } from "@/components/app/RequireRole";
import { AuthProvider, useAuth } from "@/lib/auth/AuthProvider";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/dashboard/finance",
}));

const jwt = (expSecondsFromNow: number) =>
  `h.${Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + expSecondsFromNow })).toString("base64url")}.s`;
const ok = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

const routes = vi.fn();
beforeEach(() => {
  replace.mockReset();
  routes.mockReset();
  vi.stubGlobal("fetch", routes);
});
afterEach(() => vi.unstubAllGlobals());

function Probe() {
  const auth = useAuth();
  return (
    <div>
      <span data-testid="status">{auth.status}</span>
      <span data-testid="role">{auth.role ?? "none"}</span>
      <span data-testid="error">{auth.error ?? ""}</span>
      <button onClick={() => void auth.login("a@b.com", "pw-12345678")}>login</button>
      <button onClick={() => void auth.logout()}>logout</button>
    </div>
  );
}
const mount = () =>
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );

describe("AuthProvider", () => {
  it("restores the session from the refresh cookie on load", async () => {
    routes.mockResolvedValue(ok({ access_token: jwt(900), tenant_id: "t1", role: "manager" }));
    mount();
    expect(screen.getByTestId("status")).toHaveTextContent("loading");
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
    expect(screen.getByTestId("role")).toHaveTextContent("manager");
    expect(String(routes.mock.calls[0][0])).toBe("/api/auth/refresh");
  });

  it("is anonymous when there is no valid session", async () => {
    routes.mockResolvedValue(ok({ detail: "no" }, 401));
    mount();
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anonymous"));
  });

  it("logs in, keeping only the access token and role in memory", async () => {
    routes.mockResolvedValueOnce(ok({}, 401)); // initial refresh: no session
    routes.mockResolvedValueOnce(ok({ access_token: jwt(900), tenant_id: "t1", role: "owner" }));
    mount();
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anonymous"));
    await act(async () => screen.getByText("login").click());
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
    expect(screen.getByTestId("role")).toHaveTextContent("owner");
    expect(JSON.parse(routes.mock.calls[1][1].body)).toEqual({ email: "a@b.com", password: "pw-12345678" });
    expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
  });

  it("shows a wrong password as an error and stays anonymous", async () => {
    routes.mockResolvedValueOnce(ok({}, 401));
    routes.mockResolvedValueOnce(ok({ detail: "Invalid email or password" }, 401));
    mount();
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anonymous"));
    await act(async () => screen.getByText("login").click());
    await waitFor(() => expect(screen.getByTestId("error")).toHaveTextContent("Invalid email or password"));
    expect(screen.getByTestId("status")).toHaveTextContent("anonymous");
  });

  it("logs out: tells the server, forgets the session", async () => {
    routes.mockResolvedValueOnce(ok({ access_token: jwt(900), tenant_id: "t1", role: "owner" }));
    routes.mockResolvedValueOnce(new Response(null, { status: 204 }));
    mount();
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
    await act(async () => screen.getByText("logout").click());
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anonymous"));
    expect(String(routes.mock.calls[1][0])).toBe("/api/auth/logout");
  });

  it("refreshes before the access token expires (expiry is handled, not an error page)", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      routes.mockResolvedValueOnce(ok({ access_token: jwt(120), tenant_id: "t1", role: "staff" }));
      routes.mockResolvedValueOnce(ok({ access_token: jwt(900), tenant_id: "t1", role: "staff" }));
      mount();
      await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
      expect(routes).toHaveBeenCalledTimes(1);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(70_000); // 120 s token, refresh scheduled 60 s before expiry
      });
      await waitFor(() => expect(routes).toHaveBeenCalledTimes(2));
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
    } finally {
      vi.useRealTimers();
    }
  });

  it("falls back to anonymous when the refresh at expiry is refused", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      routes.mockResolvedValueOnce(ok({ access_token: jwt(120), tenant_id: "t1", role: "staff" }));
      routes.mockResolvedValueOnce(ok({ detail: "Invalid refresh token" }, 401));
      mount();
      await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
      await act(async () => {
        await vi.advanceTimersByTimeAsync(70_000);
      });
      await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anonymous"));
    } finally {
      vi.useRealTimers();
    }
  });

  it("sends the bearer token on existing axios calls and retries once after a 401", async () => {
    const seen: (string | undefined)[] = [];
    const adapter = vi.fn(async (config: { headers: { get: (k: string) => unknown } }) => {
      const auth = config.headers.get("Authorization") as string | undefined;
      seen.push(auth);
      if (seen.length === 1) throw Object.assign(new Error("401"), { response: { status: 401 }, config });
      return { data: { ok: true }, status: 200, statusText: "OK", headers: {}, config };
    });
    const first = jwt(900);
    const second = jwt(901);
    routes.mockResolvedValueOnce(ok({ access_token: first, tenant_id: "t1", role: "owner" }));
    routes.mockResolvedValueOnce(ok({ access_token: second, tenant_id: "t1", role: "owner" }));
    mount();
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
    const res = await axios.get("http://localhost:8000/api/inventory", { adapter: adapter as never });
    expect(res.data).toEqual({ ok: true });
    expect(seen).toEqual([`Bearer ${first}`, `Bearer ${second}`]);
  });
});

describe("RequireRole: login and 403 on the web", () => {
  const renderGuard = (roles: ("owner" | "manager" | "staff")[]) =>
    render(
      <AuthProvider>
        <RequireRole roles={roles}>
          <p>secret finance page</p>
        </RequireRole>
      </AuthProvider>,
    );

  it("sends an anonymous visitor to sign-in and remembers where they were going", async () => {
    routes.mockResolvedValue(ok({}, 401));
    renderGuard(["owner"]);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/sign-in?next=%2Fdashboard%2Ffinance"));
    expect(screen.queryByText("secret finance page")).toBeNull();
  });

  it("shows the restricted view, not the page, to a role that may not see it", async () => {
    routes.mockResolvedValue(ok({ access_token: jwt(900), tenant_id: "t1", role: "staff" }));
    renderGuard(["owner", "manager"]);
    expect(await screen.findByText(/access is restricted/i)).toBeInTheDocument();
    expect(screen.queryByText("secret finance page")).toBeNull();
    expect(replace).not.toHaveBeenCalled();
  });

  it("renders the page for an allowed role", async () => {
    routes.mockResolvedValue(ok({ access_token: jwt(900), tenant_id: "t1", role: "owner" }));
    renderGuard(["owner"]);
    expect(await screen.findByText("secret finance page")).toBeInTheDocument();
  });

  it("shows a loading state, not the page, while the session is being restored", () => {
    routes.mockReturnValue(new Promise(() => undefined));
    renderGuard(["owner"]);
    expect(screen.queryByText("secret finance page")).toBeNull();
    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
  });
});
