"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button, buttonClass } from "@/components/app/Button";
import { SelectInput, TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { FormShell } from "@/components/form/FormShell";
import { ROLE_HELP } from "@/components/team/RoleGuide";
import { useSubmit } from "@/hooks/useSubmit";
import { apiPost } from "@/lib/api/client";
import type { TeamMember } from "@/lib/api/types";
import { fieldErrorsOf } from "@/lib/validation/common";
import { teamMemberSchema } from "@/lib/validation/team";

type Values = { name: string; email: string; role: string; password: string };
const blank: Values = { name: "", email: "", role: "staff", password: "" };

/** Add a team member (PRD F-019) in the mandated master-form layout. Owners only. */
export function TeamMemberForm() {
  const router = useRouter();
  const [values, setValues] = useState<Values>(blank);
  const [touched, setTouched] = useState<ReadonlySet<string>>(new Set());
  const [submitted, setSubmitted] = useState(false);
  const [done, setDone] = useState(false); // added: a second click before the page changes must not add them again

  const add = useSubmit((v: Values) =>
    apiPost<TeamMember>("/team/", { name: v.name.trim(), email: v.email.trim(), role: v.role, ...(v.password ? { password: v.password } : {}) }),
  );
  const parsed = useMemo(() => teamMemberSchema.safeParse(values), [values]);
  const liveErrors = parsed.success ? {} : fieldErrorsOf(parsed.error);
  const serverFields = { ...add.fieldErrors };
  if (add.error?.code === "password_required") serverFields.password = add.error.message;
  if (add.error?.code === "already_member") serverFields.email = add.error.message;
  const err = (field: string): string | undefined => (touched.has(field) || submitted ? liveErrors[field] : undefined) ?? serverFields[field];
  const touch = (field: string) => setTouched((prev) => new Set(prev).add(field));
  const set = (key: keyof Values, value: string) => setValues((v) => ({ ...v, [key]: value }));
  const formLevel = add.error && Object.keys(serverFields).length === 0 ? add.error.message : undefined;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (done) return;
    setSubmitted(true);
    if (!parsed.success) return;
    const made = await add.run(values);
    if (!made) return;
    setDone(true);
    toast.success(
      made.new_account
        ? `${made.name ?? made.email} can now sign in as ${made.role}. Give them the password you set.`
        : `${made.name ?? made.email} was added as ${made.role}. They sign in with their own password.`,
    );
    router.push("/team");
  }

  return (
    <form onSubmit={onSubmit} noValidate aria-label="Add team member">
      <FormShell
        mode="master"
        title="Add team member"
        actions={
          <>
            <Link href="/team" className={buttonClass("secondary")}>
              Cancel
            </Link>
            <Button type="submit" variant="primary" loading={add.pending} disabled={done}>
              Add to team
            </Button>
          </>
        }
        audit={<p>Adding a person, changing their role and removing them are recorded in the audit log. Passwords are never stored in it.</p>}
      >
        {formLevel ? (
          <p role="alert" className="mb-4 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
            {formLevel}
          </p>
        ) : null}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <FormField id="name" label="Name" required error={err("name")}>
            <TextInput id="name" autoComplete="off" value={values.name} onChange={(e) => set("name", e.target.value)} onBlur={() => touch("name")} invalid={Boolean(err("name"))} />
          </FormField>
          <FormField id="email" label="Email" required error={err("email")} hint="They sign in with this.">
            <TextInput id="email" type="email" autoComplete="off" value={values.email} onChange={(e) => set("email", e.target.value)} onBlur={() => touch("email")} invalid={Boolean(err("email"))} />
          </FormField>
          <FormField id="role" label="Role" required error={err("role")} hint={ROLE_HELP[values.role]}>
            <SelectInput id="role" value={values.role} onChange={(e) => set("role", e.target.value)}>
              <option value="staff">Staff</option>
              <option value="manager">Manager</option>
            </SelectInput>
          </FormField>
          <FormField id="password" label="First password" error={err("password")} hint="Give it to them. If they already have a BazaarFlow account they keep their own and this is ignored.">
            <TextInput id="password" type="password" autoComplete="new-password" value={values.password} onChange={(e) => set("password", e.target.value)} onBlur={() => touch("password")} invalid={Boolean(err("password"))} />
          </FormField>
        </div>
      </FormShell>
    </form>
  );
}
