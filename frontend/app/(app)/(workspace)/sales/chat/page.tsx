"use client";

import { ChatPanel } from "@/components/agent/ChatPanel";
import { PageHeader } from "@/components/app/PageHeader";

/** Sales chat (PRD F-006). Every role can use it; what the agent may do follows the signed-in role. */
export default function SalesChatPage() {
  return (
    <div className="flex flex-col">
      <PageHeader title="Sales chat" description="Record sales and ask questions by chat. Changes wait for approval." />
      <ChatPanel />
    </div>
  );
}
