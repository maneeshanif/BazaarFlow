import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FormShell } from "@/components/form/FormShell";

const inOrder = (...ids: string[]) =>
  ids.every((id) => screen.queryByTestId(id)) &&
  ids.every(
    (id, i) =>
      i === 0 ||
      !!(screen.getByTestId(ids[i - 1]).compareDocumentPosition(screen.getByTestId(id)) & Node.DOCUMENT_POSITION_FOLLOWING),
  );

describe("FormShell: the mandated layout (PRD §5.1)", () => {
  it("renders header, filters, grid, totals, actions and audit panel in that order", () => {
    render(
      <FormShell
        title="New sale"
        status="draft"
        filters={<div>master</div>}
        totals={<div>Total</div>}
        actions={<button>Post sale</button>}
        audit={<div>created by Staff</div>}
      >
        <div>grid</div>
      </FormShell>,
    );
    expect(inOrder("form-header", "form-filters", "form-grid", "form-totals", "form-actions", "form-audit")).toBe(true);
  });

  it("shows the document status as a badge with text in the header", () => {
    render(
      <FormShell title="New sale" status="posted" actions={<button>Reverse</button>} audit={<span>log</span>}>
        <div>g</div>
      </FormShell>,
    );
    expect(within(screen.getByTestId("form-header")).getByText(/posted/i)).toBeInTheDocument();
  });

  it("omits grid and totals for master-only forms but keeps the audit panel", () => {
    render(
      <FormShell mode="master" title="Shop profile" actions={<button>Save</button>} audit={<span>log</span>}>
        <div>fields</div>
      </FormShell>,
    );
    expect(screen.queryByTestId("form-grid")).toBeNull();
    expect(screen.queryByTestId("form-totals")).toBeNull();
    expect(screen.getByTestId("form-audit")).toBeInTheDocument();
    expect(screen.getByTestId("form-filters")).toHaveTextContent("fields");
  });

  it("right-aligns the actions with the primary action last", () => {
    render(
      <FormShell
        title="x"
        actions={
          <>
            <button>Cancel</button>
            <button>Save</button>
          </>
        }
        audit={<span>a</span>}
      >
        <div>g</div>
      </FormShell>,
    );
    const buttons = within(screen.getByTestId("form-actions")).getAllByRole("button");
    expect(buttons.map((b) => b.textContent)).toEqual(["Cancel", "Save"]);
    expect(screen.getByTestId("form-actions").className).toMatch(/justify-end/);
  });

  it("labels the form region by its title for assistive technology", () => {
    render(
      <FormShell title="New sale" actions={null} audit={<span>a</span>}>
        <div>g</div>
      </FormShell>,
    );
    expect(screen.getByRole("region", { name: "New sale" })).toBeInTheDocument();
  });
});
