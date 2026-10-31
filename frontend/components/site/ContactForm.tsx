"use client";

import { useState, type FormEvent } from "react";
import { CONTACT_EMAIL } from "@/components/site/content";
import { RollLabel } from "@/components/site/text";

const FIELD =
  "w-full rounded-chip bg-cream-tan px-4 py-3 text-ui-base text-forest-ink placeholder:text-forest-ink/60 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus";

/**
 * The message form. There is no mail server behind the site yet, so Send opens the visitor's own email app with the message
 * already written (a `mailto:` link). The page says so under the button.
 */
export function ContactForm() {
  const [error, setError] = useState<string | null>(null);

  function send(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const get = (k: string) => String(data.get(k) ?? "").trim();
    if (!get("name") || !get("message")) {
      setError("Please add your name and a message.");
      return;
    }
    setError(null);
    const body = [get("message"), "", `Name: ${get("name")}`, `Shop: ${get("shop") || "-"}`, `Phone: ${get("phone") || "-"}`, `Email: ${get("email") || "-"}`].join("\n");
    window.location.href = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(`BazaarFlow message from ${get("name")}`)}&body=${encodeURIComponent(body)}`;
  }

  return (
    <form onSubmit={send} noValidate className="grid gap-4 md:grid-cols-[1fr_auto]">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-1 font-display text-ui-sm uppercase tracking-wide">
          Name
          <input name="name" autoComplete="name" required className={FIELD} aria-invalid={error ? true : undefined} />
        </label>
        <label className="grid gap-1 font-display text-ui-sm uppercase tracking-wide">
          Shop
          <input name="shop" autoComplete="organization" className={FIELD} />
        </label>
        <label className="grid gap-1 font-display text-ui-sm uppercase tracking-wide">
          Phone
          <input name="phone" type="tel" autoComplete="tel" className={FIELD} />
        </label>
        <label className="grid gap-1 font-display text-ui-sm uppercase tracking-wide">
          Email
          <input name="email" type="email" autoComplete="email" className={FIELD} />
        </label>
        <label className="grid gap-1 font-display text-ui-sm uppercase tracking-wide sm:col-span-2">
          Message
          <textarea name="message" rows={5} required className={FIELD} aria-invalid={error ? true : undefined} />
        </label>
      </div>
      <button
        type="submit"
        className="roll min-h-control-lg rounded-card bg-lime px-8 font-display text-display-lg uppercase text-forest-ink shadow-card transition-transform duration-300 [transition-timing-function:var(--ease-bounce)] hover:-rotate-2 hover:scale-[1.03] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus md:[writing-mode:horizontal-tb]"
      >
        <RollLabel text="Send" />
      </button>
      <div className="md:col-span-2" aria-live="polite">
        {error ? (
          <p role="alert" className="rounded-chip border-2 border-danger-border bg-danger-subtle px-4 py-2 text-ui-sm font-bold text-danger">
            {error}
          </p>
        ) : (
          <p className="text-ui-sm font-medium text-forest-ink/80">Send opens your email app with this message ready to go. There is no mail server behind this page yet.</p>
        )}
      </div>
    </form>
  );
}
