/** What each role may do, in the words of PRD §14.2, so an owner knows what they are handing out. */
export const ROLE_HELP: Record<string, string> = {
  owner: "Runs the shop: everything, including the team, integrations and deleting.",
  manager: "Runs the day: products, sales, customers, marketing and approvals. Cannot manage the team or shop settings, and cannot delete.",
  staff: "Records sales and customers and looks up stock. Cannot see cost, finance or marketing, and cannot approve or reverse.",
};

export function RoleGuide() {
  return (
    <section aria-label="What each role can do" className="rounded-lg border border-border bg-surface p-4">
      <h2 className="text-ui-md font-semibold text-fg">What each role can do</h2>
      <dl className="mt-2 grid gap-2 text-ui-sm md:grid-cols-3">
        {(["owner", "manager", "staff"] as const).map((role) => (
          <div key={role}>
            <dt className="font-medium capitalize text-fg">{role}</dt>
            <dd className="text-fg-muted">{ROLE_HELP[role]}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
