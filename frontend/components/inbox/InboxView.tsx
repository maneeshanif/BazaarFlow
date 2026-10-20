"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/app/Button";
import { PageHeader } from "@/components/app/PageHeader";
import { ErrorState } from "@/components/app/StateViews";
import { StatusBadge } from "@/components/app/StatusBadge";
import { SelectInput, TextArea, TextInput } from "@/components/form/Controls";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { useSubmit } from "@/hooks/useSubmit";
import { apiGet, apiPatch, apiPost } from "@/lib/api/client";
import type { Conversation, ConversationDetail, InboxMessage, Page } from "@/lib/api/types";
import { formatDateTime, formatMoney } from "@/lib/format";
import { replySchema } from "@/lib/validation/channels";
import { cn } from "@/lib/utils";

const STATUSES = [
  { value: "", label: "Every conversation" },
  { value: "needs_human", label: "Needs a person" },
  { value: "ai_handling", label: "AI is answering" },
  { value: "open", label: "Open" },
  { value: "resolved", label: "Resolved" },
];

const POLL_MS = 10_000;

function Bubble({ message, onRetry }: { message: InboxMessage; onRetry: (id: string) => void }) {
  const mine = message.direction === "outbound";
  return (
    <li className={cn("flex flex-col gap-1", mine ? "items-end" : "items-start")}>
      <div className={cn("max-w-[85%] whitespace-pre-wrap rounded-lg border px-3 py-2 text-ui-base", mine ? "border-action-border bg-action-subtle text-fg" : "border-border bg-surface text-fg")}>
        {message.text}
      </div>
      <p className="flex flex-wrap items-center gap-2 text-ui-xs text-fg-muted">
        <span>{message.sender === "ai" ? "AI" : message.sender === "staff" ? "You" : "Customer"}</span>
        <span>{formatDateTime(message.created_at)}</span>
        {mine ? <StatusBadge status={message.status} /> : null}
        {message.status === "send_failed" ? (
          <>
            <span role="alert" className="text-danger">
              {message.error ?? "Not sent."}
            </span>
            <Button size="sm" onClick={() => onRetry(message.id)}>
              Retry
            </Button>
          </>
        ) : null}
      </p>
    </li>
  );
}

function Thread({ id, onChanged }: { id: string; onChanged: () => void }) {
  const detail = useLoad(() => apiGet<ConversationDetail>(`/conversations/${id}`), [id]);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const keyRef = useRef<string>("");
  const endRef = useRef<HTMLDivElement>(null);
  const { reload } = detail;

  useEffect(() => {
    const timer = setInterval(reload, POLL_MS);
    return () => clearInterval(timer);
  }, [reload]);
  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "end" });
  }, [detail.data?.messages.length]);

  const send = useSubmit((body: { text: string; idempotency_key: string }) => apiPost<InboxMessage>(`/conversations/${id}/messages`, body));
  const patch = useSubmit((body: Record<string, unknown>) => apiPatch<Conversation>(`/conversations/${id}`, body));
  const retry = useSubmit((messageId: string) => apiPost<InboxMessage>(`/conversations/${id}/messages/${messageId}/retry`));

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const parsed = replySchema.safeParse({ text });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Write a message");
      return;
    }
    setError(null);
    if (!keyRef.current) keyRef.current = `ui-${crypto.randomUUID()}`; // one key per message, so a double click sends once
    const done = await send.run({ text: parsed.data.text, idempotency_key: keyRef.current });
    if (!done) return;
    keyRef.current = "";
    setText("");
    if (done.status === "send_failed") toast.error(done.error ?? "The message could not be sent");
    reload();
    onChanged();
  }

  function onKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  }

  async function update(body: Record<string, unknown>, ok: string) {
    if (!(await patch.run(body))) return;
    toast.success(ok);
    reload();
    onChanged();
  }

  async function onRetry(messageId: string) {
    const done = await retry.run(messageId);
    if (done) toast[done.status === "sent" ? "success" : "error"](done.status === "sent" ? "Sent" : (done.error ?? "Still not sent"));
    reload();
  }

  if (detail.state === "loading" && !detail.data) return <Skeleton className="h-64 w-full" />;
  if (detail.state === "error" || !detail.data) return <ErrorState message={detail.error?.message ?? "Could not load this conversation."} onRetry={detail.reload} />;
  const { conversation, messages, context, provider_notice } = detail.data;
  const ai = conversation.mode === "ai";

  return (
    <div className="grid min-h-0 grid-cols-1 gap-3 xl:grid-cols-[1fr_16rem]">
      <section aria-label="Conversation" className="flex min-w-0 flex-col gap-3">
        <header className="flex flex-wrap items-center justify-between gap-2 rounded-card border-2 border-line-strong bg-surface-raised p-5 shadow-card">
          <div className="min-w-0">
            <h2 className="truncate text-ui-md font-semibold text-fg">{conversation.contact_name ?? conversation.phone}</h2>
            <p className="font-mono text-ui-xs text-fg-muted">{conversation.phone}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={conversation.status} />
            <div role="group" aria-label="Who answers" className="flex overflow-hidden rounded-md border border-border">
              <button type="button" aria-pressed={ai} className={cn("px-3 py-1 text-ui-sm", ai ? "bg-action text-fg-inverse" : "bg-surface text-fg")} onClick={() => !ai && void update({ mode: "ai" }, "The AI is answering again")}>
                AI
              </button>
              <button type="button" aria-pressed={!ai} className={cn("px-3 py-1 text-ui-sm", !ai ? "bg-action text-fg-inverse" : "bg-surface text-fg")} onClick={() => ai && void update({ mode: "human" }, "You have taken over")}>
                Human
              </button>
            </div>
            {conversation.status === "resolved" ? (
              <Button size="sm" onClick={() => void update({ status: "open" }, "Reopened")}>
                Reopen
              </Button>
            ) : (
              <Button size="sm" onClick={() => void update({ status: "resolved" }, "Marked as resolved")}>
                Mark resolved
              </Button>
            )}
          </div>
        </header>

        {provider_notice ? (
          <p role="status" className="rounded-md border border-warning-border bg-warning-subtle px-3 py-2 text-ui-sm text-warning">
            {provider_notice}{" "}
            <Link href="/integrations" className="font-medium underline">
              Open integrations
            </Link>
          </p>
        ) : null}
        {conversation.handoff_note && !ai ? (
          <p role="status" className="rounded-md border border-border bg-surface px-3 py-2 text-ui-sm text-fg-muted">
            Handed to a person: {conversation.handoff_note}
          </p>
        ) : null}

        <ul aria-label="Messages" className="flex max-h-[28rem] min-h-40 flex-col gap-3 overflow-y-auto rounded-card border-2 border-line-strong bg-surface-raised shadow-card-sunken p-3">
          {messages.map((m) => (
            <Bubble key={m.id} message={m} onRetry={(mid) => void onRetry(mid)} />
          ))}
          <div ref={endRef} />
        </ul>

        <form onSubmit={submit} noValidate aria-label="Reply" className="flex flex-col gap-2">
          <label htmlFor="reply" className="text-ui-xs font-medium text-fg-muted">
            Reply {ai ? "(sending takes over from the AI)" : ""}
          </label>
          <TextArea id="reply" rows={3} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKey} invalid={Boolean(error)} placeholder="Enter to send, Shift+Enter for a new line" />
          {error ?? send.error ? (
            <p role="alert" className="text-ui-sm text-danger">
              {error ?? send.error?.message}
            </p>
          ) : null}
          <div className="flex justify-end">
            <Button type="submit" variant="primary" loading={send.pending}>
              Send
            </Button>
          </div>
        </form>
      </section>

      <aside aria-label="Customer" className="flex flex-col gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-5 shadow-card text-ui-sm">
        <h3 className="text-ui-base font-semibold text-fg">Customer</h3>
        <p className="text-fg">{context.customer_name ?? "Not a saved customer"}</p>
        {context.balance !== null ? (
          <p className="text-fg-muted">
            Owes you <span className="font-mono text-fg">{formatMoney(context.balance)}</span>
          </p>
        ) : null}
        <div>
          <h4 className="text-ui-xs font-medium text-fg-muted">Recent orders</h4>
          {context.recent_orders.length === 0 ? (
            <p className="text-fg-muted">None yet.</p>
          ) : (
            <ul className="mt-1 flex flex-col gap-1">
              {context.recent_orders.map((o) => (
                <li key={o.id}>
                  <Link href={`/orders/${o.id}`} className="text-action hover:underline">
                    {formatMoney(o.total)}
                  </Link>{" "}
                  <span className="text-fg-muted">{formatDateTime(o.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h4 className="text-ui-xs font-medium text-fg-muted">Suggested</h4>
          <ul className="mt-1 list-disc pl-4 text-fg-muted">
            {context.suggested_actions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </div>
        <div className="flex flex-col gap-1">
          {context.customer_name ? (
            <Link href="/sales/new" className="text-action hover:underline">
              Record a sale
            </Link>
          ) : (
            <Link href="/customers/new" className="text-action hover:underline">
              Add as a customer
            </Link>
          )}
        </div>
      </aside>
    </div>
  );
}

/** The unified inbox (PRD F-005): conversations, a thread, and the customer beside it. Every role in the shop. */
export function InboxView() {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    const next = search.trim();
    if (next === q) return;
    const id = setTimeout(() => setQ(next), 300);
    return () => clearTimeout(id);
  }, [search, q]);

  const list = useLoad(() => apiGet<Page<Conversation>>("/conversations/", { status: status || undefined, q: q || undefined, limit: 50 }), [status, q], (page) => page.items.length === 0);
  const { reload } = list;
  useEffect(() => {
    const timer = setInterval(reload, POLL_MS);
    return () => clearInterval(timer);
  }, [reload]);
  const items = list.data?.items ?? [];

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Inbox" description="Customer messages from WhatsApp. The AI answers prices and stock; you take over any time." />
      <div className="grid min-h-0 grid-cols-1 gap-3 lg:grid-cols-[18rem_1fr]">
        <section aria-label="Conversations" className={cn("flex min-w-0 flex-col gap-2", selected && "hidden lg:flex")}>
          <div className="flex flex-col gap-2 rounded-card border-2 border-line-strong bg-surface-raised p-5 shadow-card" role="search" aria-label="Filter conversations">
            <label htmlFor="inbox-search" className="text-ui-xs font-medium text-fg-muted">
              Search
            </label>
            <TextInput id="inbox-search" type="search" placeholder="Name or phone" value={search} onChange={(e) => setSearch(e.target.value)} />
            <label htmlFor="inbox-status" className="text-ui-xs font-medium text-fg-muted">
              Show
            </label>
            <SelectInput id="inbox-status" value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </SelectInput>
          </div>
          {list.state === "loading" && !list.data ? <Skeleton className="h-40 w-full" /> : null}
          {list.state === "error" ? <ErrorState message={list.error?.message ?? "Could not load conversations."} onRetry={list.reload} /> : null}
          {list.state === "empty" ? (
            <p className="rounded-card border-2 border-line-strong bg-surface-raised p-5 shadow-card text-ui-sm text-fg-muted">
              {q || status ? "No conversations match." : "No customer messages yet. Connect WhatsApp in Integrations and messages will appear here."}
            </p>
          ) : null}
          <ul className="flex flex-col gap-1">
            {items.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => setSelected(c.id)}
                  aria-current={selected === c.id}
                  className={cn("flex w-full flex-col gap-1 rounded-lg border p-3 text-left hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus", selected === c.id ? "border-action-border bg-action-subtle" : "border-border bg-surface")}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="truncate text-ui-base font-medium text-fg">{c.contact_name ?? c.phone}</span>
                    <StatusBadge status={c.status} />
                  </span>
                  <span className="truncate text-ui-sm text-fg-muted">{c.last_message_text}</span>
                  <span className="text-ui-xs text-fg-muted">{formatDateTime(c.last_message_at)}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        <div className={cn("min-w-0", !selected && "hidden lg:block")}>
          {selected ? (
            <>
              <Button size="sm" className="mb-2 lg:hidden" onClick={() => setSelected(null)}>
                Back to conversations
              </Button>
              <Thread key={selected} id={selected} onChanged={reload} />
            </>
          ) : (
            <p className="rounded-card border-2 border-line-strong bg-surface-raised shadow-card p-6 text-ui-sm text-fg-muted">Choose a conversation to read it.</p>
          )}
        </div>
      </div>
    </div>
  );
}
