"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/app/Button";
import { LookupDialog } from "@/components/app/LookupDialog";
import { SelectInput, TextArea } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { FormShell } from "@/components/form/FormShell";
import { useSubmit } from "@/hooks/useSubmit";
import { apiGet, apiPost } from "@/lib/api/client";
import type { MarketingPost, Page, Product } from "@/lib/api/types";
import { fieldErrorsOf } from "@/lib/validation/common";
import { briefSchema } from "@/lib/validation/marketing";

type Values = { goal: string; tone: string; language: string; productId: string; notes: string };
const blank: Values = { goal: "general", tone: "friendly", language: "english", productId: "", notes: "" };

const GOALS = [
  { value: "general", label: "A friendly update from the shop" },
  { value: "promote_product", label: "Promote a product" },
  { value: "announce_offer", label: "Announce an offer" },
  { value: "festival_greeting", label: "Greet customers for a festival" },
];

/** Ask the assistant for a draft (PRD F-014). The draft is saved for you to edit; nothing is posted anywhere. */
export function DraftBriefForm() {
  const router = useRouter();
  const [values, setValues] = useState<Values>(blank);
  const [product, setProduct] = useState<Product | null>(null);
  const [picking, setPicking] = useState(false);
  const [touched, setTouched] = useState<ReadonlySet<string>>(new Set());
  const [submitted, setSubmitted] = useState(false);
  const [done, setDone] = useState(false);

  const draft = useSubmit((v: Values) =>
    apiPost<MarketingPost>("/marketing/posts/drafts", {
      goal: v.goal,
      tone: v.tone,
      language: v.language,
      ...(v.goal === "promote_product" && v.productId ? { product_id: v.productId } : {}),
      ...(v.notes.trim() ? { notes: v.notes.trim() } : {}),
    }),
  );
  const parsed = useMemo(() => briefSchema.safeParse(values), [values]);
  const live = parsed.success ? {} : fieldErrorsOf(parsed.error);
  const err = (field: string): string | undefined => (touched.has(field) || submitted ? live[field] : undefined) ?? draft.fieldErrors[field];
  const touch = (field: string) => setTouched((prev) => new Set(prev).add(field));
  const set = (key: keyof Values, value: string) => setValues((v) => ({ ...v, [key]: value }));
  const formLevel = draft.error && Object.keys(draft.fieldErrors).length === 0 ? draft.error.message : undefined;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (done) return;
    setSubmitted(true);
    if (!parsed.success) return;
    const post = await draft.run(values);
    if (!post) return;
    setDone(true);
    toast.success("Draft ready. Read it, change what you like, then send it for approval.");
    router.push(`/marketing/${post.id}`);
  }

  return (
    <form onSubmit={onSubmit} noValidate aria-label="Draft a post">
      <FormShell
        mode="master"
        title="Draft a post"
        actions={
          <Button type="submit" variant="primary" loading={draft.pending} disabled={done}>
            Write the draft
          </Button>
        }
        audit={<p>The assistant only writes text. Nothing is posted to Facebook, and every draft is recorded in Agent activity.</p>}
      >
        {formLevel ? (
          <p role="alert" className="mb-4 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
            {formLevel}
          </p>
        ) : null}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <FormField id="goal" label="What is the post for?" required error={err("goal")}>
            <SelectInput id="goal" value={values.goal} onChange={(e) => set("goal", e.target.value)}>
              {GOALS.map((g) => (
                <option key={g.value} value={g.value}>
                  {g.label}
                </option>
              ))}
            </SelectInput>
          </FormField>
          <FormField id="tone" label="Tone" required>
            <SelectInput id="tone" value={values.tone} onChange={(e) => set("tone", e.target.value)}>
              <option value="friendly">Friendly</option>
              <option value="professional">Professional</option>
              <option value="festive">Festive</option>
            </SelectInput>
          </FormField>
          <FormField id="language" label="Language" required>
            <SelectInput id="language" value={values.language} onChange={(e) => set("language", e.target.value)}>
              <option value="english">English</option>
              <option value="roman_urdu">Roman Urdu</option>
            </SelectInput>
          </FormField>
          {values.goal === "promote_product" ? (
            <FormField id="productId" label="Product" required error={err("productId")}>
              <Button
                id="productId"
                onClick={() => setPicking(true)}
                aria-haspopup="dialog"
                aria-label={`Product: ${product ? product.name : "none chosen"}. ${product ? "Change" : "Choose"}`}
                className="w-full justify-between"
              >
                {product ? product.name : "Choose a product"}
              </Button>
            </FormField>
          ) : null}
          <FormField id="notes" label="Anything it should mention?" error={err("notes")} hint="For example the offer, the dates or the price you want to show. It will not invent prices." className="md:col-span-2">
            <TextArea id="notes" rows={3} maxLength={300} value={values.notes} onChange={(e) => set("notes", e.target.value)} onBlur={() => touch("notes")} invalid={Boolean(err("notes"))} />
          </FormField>
        </div>
      </FormShell>
      <LookupDialog<Product>
        open={picking}
        onOpenChange={setPicking}
        title="Choose a product"
        description="Search by name or SKU."
        placeholder="Name or SKU"
        load={async (q) => (await apiGet<Page<Product>>("/inventory/", { q, active: true, limit: 20 })).items}
        keyOf={(p) => p.id}
        render={(p) => (
          <span className="flex flex-col">
            <span className="font-medium">{p.name}</span>
            <span className="font-mono text-ui-xs text-fg-muted">{p.sku}</span>
          </span>
        )}
        onSelect={(p) => {
          setProduct(p);
          set("productId", p.id);
          touch("productId");
        }}
        emptyMessage="No product matches. Check the spelling or add it in Products."
      />
    </form>
  );
}
