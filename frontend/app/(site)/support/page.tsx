import type { Metadata } from "next";
import { Phone } from "lucide-react";
import { Bob } from "@/components/site/motion";
import { ProductPage } from "@/components/site/ProductPage";

export const metadata: Metadata = {
  title: "Voice support - BazaarFlow",
  description: "A voice assistant that answers customers' calls with your shop's own details, and writes every call down.",
};

const STEPS = [
  { title: "A customer calls", text: "The call comes to your shop's support line instead of ringing out.", note: "Incoming call", tone: "bg-sunny" },
  { title: "The assistant answers", text: "It answers from your shop's own details: opening hours, what is in stock, where an order is.", note: "Open till 9 pm", tone: "bg-cream" },
  { title: "It knows its limits", text: "If it cannot help, it takes a message or hands over to a person, and never makes up an answer.", note: "Message taken", tone: "bg-lime" },
  { title: "The call is written down", text: "Every call is logged with what was asked and what was said. Names and phone numbers are hidden in the log.", note: "Logged", tone: "bg-sky" },
];

const FACTS = [
  { label: "The call screen", text: "A screen in the app where you can try the assistant and see the conversation." },
  { label: "Call logs", text: "Every conversation is kept with the tools it used, with private details hidden." },
  { label: "Phone line", text: "Answering real phone calls needs the voice service. It is being connected.", later: true },
  { label: "WhatsApp orders", text: "Messages arriving in the inbox next to their orders, once the shop's account is connected.", later: true },
];

export default function SupportPage() {
  return (
    <ProductPage
      chip="Voice support"
      lines={["A phone that", "answers."]}
      lead="A voice assistant takes your customers' calls and answers from your shop's own details. Every call is written down."
      steps={STEPS}
      stepsTitle="From ring to written down."
      facts={FACTS}
      factsTitle="What works, and what is next."
      visual={
        <Bob amount={14} seconds={4}>
          <div aria-hidden className="mx-auto w-full max-w-xs -rotate-2 rounded-card bg-forest p-6 text-cream shadow-card">
            <div className="mx-auto grid h-20 w-20 place-items-center rounded-full bg-lime text-forest-ink">
              <Phone className="h-9 w-9" />
            </div>
            <p className="mt-4 text-center font-display text-ui-2xl uppercase">Shop support</p>
            <p className="mt-1 text-center text-ui-sm">Listening...</p>
            <p className="mt-6 rounded-chip bg-cream px-4 py-3 font-slip text-ui-base text-forest-ink">&ldquo;Is the shop open on Sunday?&rdquo;</p>
            <p className="mt-3 rounded-chip bg-lime px-4 py-3 text-ui-sm font-medium text-forest-ink">Yes, 10 am to 6 pm.</p>
          </div>
        </Bob>
      }
    />
  );
}
