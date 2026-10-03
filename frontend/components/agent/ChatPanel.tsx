"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ApprovalCard } from "@/components/agent/ApprovalCard";
import { Button } from "@/components/app/Button";
import { StatusBadge } from "@/components/app/StatusBadge";
import { TextArea } from "@/components/form/Controls";
import { useLoad } from "@/hooks/useLoad";
import { useSubmit } from "@/hooks/useSubmit";
import { apiGet, apiPost } from "@/lib/api/client";
import type { Approval, ChatAction, ChatResponse } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { cn } from "@/lib/utils";

type Message =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; text: string; actions: ChatAction[]; notice?: string | null; tone: "normal" | "warning" };

const EXAMPLES = [
  "sell 2 shirt to Ali",
  "2 shirt bech do Ali ko",
  "what did I sell today?",
  "how much does Ali owe?",
];

const uid = (): string => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : String(Math.random()));

/** A proposal in the chat: managers get the live approval card, staff see that it is waiting for one. */
function ProposalCard({ action, canDecide }: { action: ChatAction; canDecide: boolean }) {
  const loaded = useLoad(() => (canDecide ? apiGet<Approval>(`/approvals/${action.id}`) : Promise.resolve(null)), [action.id, canDecide]);
  const [override, setOverride] = useState<Approval | null>(null);
  if (!canDecide) {
    return (
      <div className="rounded-lg border border-border bg-surface p-3 text-ui-sm" aria-label={`Request: ${action.summary}`}>
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium text-fg">{action.summary}</span>
          <StatusBadge status={action.status} />
        </div>
        <p className="mt-1 text-fg-muted">Waiting for a manager or the owner to approve it. Nothing has changed yet.</p>
      </div>
    );
  }
  const approval = override ?? loaded.data;
  if (!approval) {
    return (
      <div className="rounded-lg border border-border bg-surface p-3 text-ui-sm text-fg-muted" role="status">
        {loaded.state === "error" ? "Could not load this request." : "Loading the request..."}
      </div>
    );
  }
  return <ApprovalCard approval={approval} canDecide onChanged={setOverride} />;
}

/**
 * The sales chat (PRD F-006): tell the agent what you sold, in English or Roman Urdu. It shows a draft first; on "yes"
 * it files an approval instead of changing anything. The card appears right in the conversation.
 */
export function ChatPanel() {
  const { role } = useAuth();
  const canDecide = role === "owner" || role === "manager";
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const sessionId = useRef<string | undefined>(undefined);
  const endRef = useRef<HTMLDivElement | null>(null);

  const send = useSubmit((text: string) => apiPost<ChatResponse>("/chat/sales", { message: text, session_id: sessionId.current }));

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "end" });
  }, [messages.length, send.pending]);

  async function submit(text: string) {
    const value = text.trim();
    if (!value || send.pending) return;
    setDraft("");
    setMessages((m) => [...m, { id: uid(), role: "user", text: value }]);
    const reply = await send.run(value);
    if (!reply) return;
    sessionId.current = reply.session_id;
    setMessages((m) => [
      ...m,
      { id: uid(), role: "assistant", text: reply.reply, actions: reply.actions, notice: reply.notice, tone: reply.outcome === "ok" ? "normal" : "warning" },
    ]);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void submit(draft);
  }
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit(draft);
    }
  }

  return (
    <section aria-label="Sales chat" className="flex min-h-[28rem] max-w-3xl flex-col gap-3">
      <div className="flex-1 overflow-y-auto rounded-lg border border-border bg-surface p-4" aria-live="polite" aria-relevant="additions">
        {messages.length === 0 ? (
          <div className="flex flex-col items-start gap-3">
            <p className="text-ui-md font-semibold text-fg">Tell me what you sold</p>
            <p className="max-w-prose text-ui-sm text-fg-muted">
              I show you a draft first. When you say yes, I send the sale to a manager or the owner for approval, and the stock changes only once it is approved. You can write in English or Roman Urdu.
            </p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((example) => (
                <Button key={example} size="sm" onClick={() => setDraft(example)}>
                  {example}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <ol className="flex flex-col gap-3">
            {messages.map((m) => (
              <li key={m.id} className={cn("flex flex-col gap-2", m.role === "user" ? "items-end" : "items-start")}>
                <div
                  className={cn(
                    "max-w-[85%] whitespace-pre-line rounded-lg px-3 py-2 text-ui-base",
                    m.role === "user"
                      ? "bg-action text-fg-inverse"
                      : m.tone === "warning"
                        ? "border border-warning-border bg-warning-subtle text-fg"
                        : "border border-border bg-surface-sunken text-fg",
                  )}
                >
                  <span className="sr-only">{m.role === "user" ? "You: " : "Assistant: "}</span>
                  {m.text}
                </div>
                {m.role === "assistant" && m.notice ? <p className="text-ui-xs text-warning">{m.notice}</p> : null}
                {m.role === "assistant" && m.actions.length > 0 ? (
                  <div className="flex w-full max-w-xl flex-col gap-2">
                    {m.actions.map((a) => (
                      <ProposalCard key={a.id} action={a} canDecide={canDecide} />
                    ))}
                  </div>
                ) : null}
              </li>
            ))}
            {send.pending ? (
              <li className="text-ui-sm text-fg-muted" role="status">
                Thinking...
              </li>
            ) : null}
          </ol>
        )}
        {send.error ? (
          <p role="alert" className="mt-3 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
            {send.error.message}
          </p>
        ) : null}
        <div ref={endRef} />
      </div>

      <form onSubmit={onSubmit} aria-label="Message the sales agent" className="flex items-end gap-2">
        <label htmlFor="chat-message" className="sr-only">
          Your message
        </label>
        <TextArea id="chat-message" rows={2} maxLength={2000} placeholder="For example: sell 2 shirt to Ali" value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={onKeyDown} className="min-h-12 flex-1" />
        <Button type="submit" variant="primary" size="lg" loading={send.pending} disabled={draft.trim() === ""}>
          Send
        </Button>
      </form>
    </section>
  );
}
