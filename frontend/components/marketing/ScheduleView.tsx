"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button, buttonClass } from "@/components/app/Button";
import { PageHeader } from "@/components/app/PageHeader";
import { ErrorState } from "@/components/app/StateViews";
import { Checkbox, SelectInput, TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { useSubmit } from "@/hooks/useSubmit";
import { apiGet, apiPut } from "@/lib/api/client";
import type { MarketingSchedule } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { fieldErrorsOf } from "@/lib/validation/common";
import { scheduleSchema } from "@/lib/validation/channels";

type Values = {
  enabled: boolean;
  goal: string;
  notes: string;
  tone: string;
  language: string;
  posts_per_day: string;
  window_start: string;
  window_end: string;
  approval_mode: string;
};

const hhmm = (t: string) => t.slice(0, 5);
const toValues = (s: MarketingSchedule): Values => ({
  enabled: s.enabled,
  goal: s.goal ?? "general",
  notes: s.notes ?? "",
  tone: s.tone ?? "friendly",
  language: s.language ?? "english",
  posts_per_day: String(s.posts_per_day ?? 1),
  window_start: hhmm(s.window_start ?? "10:00"),
  window_end: hhmm(s.window_end ?? "20:00"),
  approval_mode: s.approval_mode ?? "manual",
});

function Form({ schedule, onSaved }: { schedule: MarketingSchedule; onSaved: () => void }) {
  const [values, setValues] = useState<Values>(toValues(schedule));
  const [submitted, setSubmitted] = useState(false);
  const save = useSubmit((body: unknown) => apiPut<MarketingSchedule>("/marketing/schedule", body));
  const parsed = scheduleSchema.safeParse(values);
  const live = parsed.success ? {} : fieldErrorsOf(parsed.error);
  const err = (name: string) => (submitted ? live[name] : undefined) ?? save.fieldErrors[name];
  const formLevel = save.error && Object.keys(save.fieldErrors).length === 0 ? save.error.message : undefined;
  const set = (key: keyof Values, value: string | boolean) => setValues((v) => ({ ...v, [key]: value }));

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    if (!parsed.success) return;
    const body = { ...parsed.data, notes: parsed.data.notes || null };
    if (!(await save.run(body))) return;
    toast.success("Saved your posting schedule");
    onSaved();
  }

  return (
    <form onSubmit={onSubmit} noValidate aria-label="Posting schedule" className="flex max-w-form flex-col gap-4 rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
      {formLevel ? (
        <p role="alert" className="rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
          {formLevel}
        </p>
      ) : null}
      {!schedule.facebook_connected ? (
        <p role="status" className="rounded-md border border-warning-border bg-warning-subtle px-3 py-2 text-ui-sm text-warning">
          Facebook is not connected, so the schedule cannot be switched on.{" "}
          <Link href="/integrations" className="font-medium underline">
            Connect Facebook
          </Link>
        </p>
      ) : null}
      <label className="flex items-center gap-2 text-ui-base text-fg">
        <Checkbox checked={values.enabled} onChange={(e) => set("enabled", e.target.checked)} />
        Post to my Facebook page automatically
      </label>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <FormField id="sch-goal" label="What the posts are about" error={err("goal")}>
          <SelectInput id="sch-goal" value={values.goal} onChange={(e) => set("goal", e.target.value)}>
            <option value="general">A friendly update from the shop</option>
            <option value="announce_offer">An offer</option>
            <option value="festival_greeting">A festival greeting</option>
          </SelectInput>
        </FormField>
        <FormField id="sch-count" label="Posts per day" required error={err("posts_per_day")} hint="1 to 5, spread evenly across the window.">
          <TextInput id="sch-count" inputMode="numeric" value={values.posts_per_day} onChange={(e) => set("posts_per_day", e.target.value)} invalid={Boolean(err("posts_per_day"))} />
        </FormField>
        <FormField id="sch-start" label="Window starts" required error={err("window_start")} hint="Your shop's local time.">
          <TextInput id="sch-start" type="time" value={values.window_start} onChange={(e) => set("window_start", e.target.value)} invalid={Boolean(err("window_start"))} />
        </FormField>
        <FormField id="sch-end" label="Window ends" required error={err("window_end")}>
          <TextInput id="sch-end" type="time" value={values.window_end} onChange={(e) => set("window_end", e.target.value)} invalid={Boolean(err("window_end"))} />
        </FormField>
        <FormField id="sch-tone" label="Tone" error={err("tone")}>
          <SelectInput id="sch-tone" value={values.tone} onChange={(e) => set("tone", e.target.value)}>
            <option value="friendly">Friendly</option>
            <option value="professional">Professional</option>
            <option value="festive">Festive</option>
          </SelectInput>
        </FormField>
        <FormField id="sch-lang" label="Language" error={err("language")}>
          <SelectInput id="sch-lang" value={values.language} onChange={(e) => set("language", e.target.value)}>
            <option value="english">English</option>
            <option value="roman_urdu">Roman Urdu</option>
          </SelectInput>
        </FormField>
        <FormField id="sch-approval" label="Before a post goes out" error={err("approval_mode")} hint="With approval, each post waits in Approvals until you accept it.">
          <SelectInput id="sch-approval" value={values.approval_mode} onChange={(e) => set("approval_mode", e.target.value)}>
            <option value="manual">I approve each post</option>
            <option value="auto">Publish without asking</option>
          </SelectInput>
        </FormField>
        <FormField id="sch-notes" label="Notes for the writer" error={err("notes")} hint="For example: Eid sale, 20% off all shirts." className="md:col-span-2">
          <TextInput id="sch-notes" value={values.notes} onChange={(e) => set("notes", e.target.value)} invalid={Boolean(err("notes"))} />
        </FormField>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-ui-sm text-fg-muted">
          {schedule.next_post_at ? `Next post: ${formatDateTime(schedule.next_post_at)}` : "No post is queued right now."}{" "}
          <Link href="/marketing/activity" className="text-action hover:underline">
            See activity
          </Link>
        </p>
        <Button type="submit" variant="primary" loading={save.pending}>
          Save schedule
        </Button>
      </div>
    </form>
  );
}

/** The posting schedule (PRD F-015). Owners and managers. */
export function ScheduleView() {
  const loaded = useLoad(() => apiGet<MarketingSchedule>("/marketing/schedule"), []);
  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Posting schedule"
        description="Let the marketing assistant write and post for you on a plan."
        actions={
          <Link href="/marketing" className={buttonClass("secondary")}>
            Marketing studio
          </Link>
        }
      />
      {loaded.state === "loading" ? <Skeleton className="h-64 max-w-form" /> : null}
      {loaded.state === "error" ? <ErrorState message={loaded.error?.message ?? "Could not load the schedule."} onRetry={loaded.reload} /> : null}
      {loaded.data ? <Form key={`${loaded.data.enabled}-${loaded.data.facebook_connected}-${loaded.data.posts_per_day}`} schedule={loaded.data} onSaved={loaded.reload} /> : null}
    </div>
  );
}
