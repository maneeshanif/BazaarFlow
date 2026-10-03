"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Button, buttonClass } from "@/components/app/Button";
import { ConfirmDialog } from "@/components/app/ConfirmDialog";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { RequireRole } from "@/components/app/RequireRole";
import { SelectInput } from "@/components/form/Controls";
import { RoleGuide } from "@/components/team/RoleGuide";
import { useLoad } from "@/hooks/useLoad";
import { useSubmit } from "@/hooks/useSubmit";
import { apiDelete, apiGet, apiPatch } from "@/lib/api/client";
import type { TeamMember } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

type Row = TeamMember & { person: string; since: string; actions: string };

function TeamList() {
  const list = useLoad(() => apiGet<TeamMember[]>("/team/"), [], (members) => members.length === 0);
  const [removing, setRemoving] = useState<TeamMember | null>(null);

  const changeRole = useSubmit((member: TeamMember, role: string) => apiPatch<TeamMember>(`/team/${member.id}`, { role }));
  const remove = useSubmit(async (member: TeamMember) => {
    await apiDelete(`/team/${member.id}`);
    return member;
  });

  async function onRole(member: TeamMember, role: string) {
    const done = await changeRole.run(member, role);
    if (!done) return;
    toast.success(`${done.name ?? done.email} is now ${done.role}. It applies from their next action.`);
    list.reload();
  }

  async function onRemove() {
    if (!removing) return;
    const done = await remove.run(removing);
    if (!done) return;
    toast.success(`${done.name ?? done.email} was removed and signed out of your shop.`);
    setRemoving(null);
    list.reload();
  }

  const rows: Row[] = useMemo(
    () => (list.data ?? []).map((m) => ({ ...m, person: m.name ?? m.email, since: formatDate(m.joined_at), actions: m.id })),
    [list.data],
  );

  const columns: Column<Row>[] = [
    {
      key: "person",
      header: "Name",
      render: (r) => (
        <span className="flex flex-col">
          <span className="font-medium text-fg">
            {r.person}
            {r.is_you ? <span className="ml-2 text-ui-xs font-normal text-fg-muted">(you)</span> : null}
          </span>
          <span className="text-ui-xs text-fg-muted">{r.email}</span>
        </span>
      ),
    },
    {
      key: "role",
      header: "Role",
      render: (r) =>
        r.role === "owner" ? (
          <span className="capitalize">owner</span>
        ) : (
          <SelectInput aria-label={`Role of ${r.person}`} value={r.role} disabled={changeRole.pending} onChange={(e) => void onRole(r, e.target.value)} className="w-32">
            <option value="manager">Manager</option>
            <option value="staff">Staff</option>
          </SelectInput>
        ),
    },
    { key: "since", header: "Joined" },
    {
      key: "actions",
      header: "",
      render: (r) =>
        r.role === "owner" ? null : (
          <Button variant="ghost" size="sm" onClick={() => setRemoving(r)} aria-label={`Remove ${r.person}`}>
            Remove
          </Button>
        ),
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Team"
        description="The people who work in your shop and what each of them can do."
        actions={
          <Link href="/team/new" className={buttonClass("primary")}>
            Add team member
          </Link>
        }
      />
      {changeRole.error ? (
        <p role="alert" className="rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
          {changeRole.error.message}
        </p>
      ) : null}
      <DataTable
        caption="Team"
        columns={columns}
        rows={rows}
        state={list.state}
        rowKey={(r) => r.id}
        emptyMessage="Your team is just you for now."
        errorMessage={list.error?.message ?? "Could not load your team."}
        onRetry={list.reload}
      />
      <RoleGuide />
      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(open) => !open && setRemoving(null)}
        title={`Remove ${removing?.name ?? removing?.email ?? "this person"}?`}
        confirmLabel="Remove from team"
        pending={remove.pending}
        onConfirm={() => void onRemove()}
      >
        <p>
          They are signed out of your shop straight away and cannot sign in to it again unless you add them back. Their past sales stay on record.
        </p>
        {remove.error ? (
          <p role="alert" className="mt-2 text-danger">
            {remove.error.message}
          </p>
        ) : null}
      </ConfirmDialog>
    </div>
  );
}

/** Team and roles (PRD F-019). Owner only. */
export default function TeamPage() {
  return (
    <RequireRole roles={["owner"]}>
      <TeamList />
    </RequireRole>
  );
}
