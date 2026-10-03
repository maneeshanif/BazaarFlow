"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button, buttonClass } from "@/components/app/Button";
import { ConfirmDialog } from "@/components/app/ConfirmDialog";
import { StatusBadge } from "@/components/app/StatusBadge";
import { TextArea, TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { FormShell } from "@/components/form/FormShell";
import { useSubmit } from "@/hooks/useSubmit";
import { apiDelete, apiPatch, apiPost } from "@/lib/api/client";
import type { MarketingPost } from "@/lib/api/types";
import { fieldErrorsOf } from "@/lib/validation/common";
import { normaliseHashtags, postSchema } from "@/lib/validation/marketing";

type Values = { title: string; message: string; hashtags: string };

/**
 * One post (PRD F-014). A draft can be edited, sent for approval or removed; a post that is waiting or approved is
 * read-only and says what happens next. Approving marks it ready: publishing arrives with the Facebook channel.
 */
export function PostEditor({ post: initial }: { post: MarketingPost }) {
  const router = useRouter();
  const [post, setPost] = useState(initial);
  const [values, setValues] = useState<Values>({ title: initial.title, message: initial.message, hashtags: initial.hashtags });
  const [touched, setTouched] = useState<ReadonlySet<string>>(new Set());
  const [submitted, setSubmitted] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [gone, setGone] = useState(false);

  const save = useSubmit((v: Values) => apiPatch<MarketingPost>(`/marketing/posts/${post.id}`, { ...v, hashtags: normaliseHashtags(v.hashtags) }));
  const send = useSubmit(() => apiPost<MarketingPost>(`/marketing/posts/${post.id}/submit`));
  const remove = useSubmit(async () => {
    await apiDelete(`/marketing/posts/${post.id}`);
    return true;
  });

  const parsed = useMemo(() => postSchema.safeParse(values), [values]);
  const live = parsed.success ? {} : fieldErrorsOf(parsed.error);
  const err = (field: string): string | undefined => (touched.has(field) || submitted ? live[field] : undefined) ?? save.fieldErrors[field];
  const touch = (field: string) => setTouched((prev) => new Set(prev).add(field));
  const set = (key: keyof Values, value: string) => setValues((v) => ({ ...v, [key]: value }));
  const editable = post.status === "draft";
  const dirty = values.title !== post.title || values.message !== post.message || normaliseHashtags(values.hashtags) !== post.hashtags;
  const formLevel = [save.error, send.error, remove.error].find((e) => e && Object.keys(save.fieldErrors).length === 0)?.message;

  async function onSave(event?: FormEvent): Promise<MarketingPost | null> {
    event?.preventDefault();
    setSubmitted(true);
    if (!parsed.success) return null;
    const saved = await save.run(values);
    if (!saved) return null;
    setPost(saved);
    setValues({ title: saved.title, message: saved.message, hashtags: saved.hashtags });
    if (event) toast.success("Saved.");
    return saved;
  }

  async function onSend() {
    if (dirty && !(await onSave())) return;
    setSubmitted(true);
    if (!parsed.success) return;
    const sent = await send.run();
    if (!sent) return;
    setPost(sent);
    toast.success("Sent for approval. A manager or the owner will see it in Approvals.");
  }

  async function onRemove() {
    if (!(await remove.run())) return;
    setGone(true);
    toast.success("The draft was removed.");
    router.push("/marketing");
  }

  return (
    <form onSubmit={(e) => void onSave(e)} noValidate aria-label="Post">
      <FormShell
        mode="master"
        title={editable ? "Edit the draft" : "Post"}
        actions={
          <>
            <Link href="/marketing" className={buttonClass("secondary")}>
              Back to the studio
            </Link>
            {editable ? (
              <>
                <Button variant="danger" onClick={() => setRemoving(true)}>
                  Remove draft
                </Button>
                <Button type="submit" loading={save.pending} disabled={!dirty || gone}>
                  Save changes
                </Button>
                <Button variant="primary" loading={send.pending} disabled={gone} onClick={() => void onSend()}>
                  Send for approval
                </Button>
              </>
            ) : null}
          </>
        }
        audit={<p>Drafts, edits, approvals and removals are recorded in the audit log. Nothing is posted to Facebook yet: approving only marks the post ready.</p>}
      >
        <p className="mb-4 flex flex-wrap items-center gap-2 text-ui-sm text-fg-muted">
          <StatusBadge status={post.status} />
          {post.status === "draft" ? "Only you can see it until you send it for approval." : null}
          {post.status === "pending_approval" ? (
            <span>
              Waiting for a manager or the owner.{" "}
              <Link href="/approvals" className="font-medium text-action hover:underline">
                Open Approvals
              </Link>
            </span>
          ) : null}
          {post.status === "approved" ? "Approved and ready. Publishing to Facebook arrives in a later update." : null}
        </p>
        {formLevel ? (
          <p role="alert" className="mb-4 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
            {formLevel}
          </p>
        ) : null}
        <div className="grid grid-cols-1 gap-4">
          <FormField id="title" label="Title" required error={err("title")}>
            <TextInput id="title" maxLength={120} readOnly={!editable} value={values.title} onChange={(e) => set("title", e.target.value)} onBlur={() => touch("title")} invalid={Boolean(err("title"))} />
          </FormField>
          <FormField id="message" label="Message" required error={err("message")} hint={`${values.message.length} of 1000 characters`}>
            <TextArea id="message" rows={6} maxLength={1000} readOnly={!editable} value={values.message} onChange={(e) => set("message", e.target.value)} onBlur={() => touch("message")} invalid={Boolean(err("message"))} />
          </FormField>
          <FormField id="hashtags" label="Hashtags" error={err("hashtags")} hint="Separate them with spaces. Up to 10.">
            <TextInput id="hashtags" readOnly={!editable} value={values.hashtags} onChange={(e) => set("hashtags", e.target.value)} onBlur={() => touch("hashtags")} invalid={Boolean(err("hashtags"))} />
          </FormField>
        </div>
      </FormShell>
      <ConfirmDialog open={removing} onOpenChange={setRemoving} title={`Remove "${post.title}"?`} confirmLabel="Remove draft" pending={remove.pending} onConfirm={() => void onRemove()}>
        The draft disappears from the studio. This is recorded in the audit log.
      </ConfirmDialog>
    </form>
  );
}
