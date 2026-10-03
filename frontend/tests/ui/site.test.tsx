import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

import { StartDemoButton } from "@/components/site/StartDemoButton";

const fetchMock = vi.fn();
beforeEach(() => {
  push.mockReset();
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

describe("Start the live demo (PRD F-027)", () => {
  it("starts one shop for a double click and opens the dashboard", async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({}) });
    render(<StartDemoButton />);
    await userEvent.dblClick(screen.getByRole("button", { name: "Try the live demo" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/demo/start", expect.objectContaining({ method: "POST" }));
  });

  it("says why when the limit is reached, and lets you try again", async () => {
    fetchMock.mockResolvedValueOnce({ ok: false, json: async () => ({ detail: "You have started several demos already." }) });
    render(<StartDemoButton />);
    await userEvent.click(screen.getByRole("button", { name: "Try the live demo" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("started several demos");
    expect(push).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Try the live demo" })).toBeEnabled();
  });

  it("explains a network failure", async () => {
    fetchMock.mockRejectedValueOnce(new Error("offline"));
    render(<StartDemoButton />);
    await userEvent.click(screen.getByRole("button", { name: "Try the live demo" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not reach the server");
  });
});
