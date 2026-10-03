"use client";

import { useState } from "react";
import { Button } from "@/components/app/Button";
import { LookupDialog } from "@/components/app/LookupDialog";
import { apiGet } from "@/lib/api/client";
import type { Page, Product } from "@/lib/api/types";
import { formatMoney } from "@/lib/format";

/** Adds a product to the sale: a search dialog over the catalogue (products for sale only). */
export function ProductPicker({ onPick }: { onPick: (product: Product) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)} aria-haspopup="dialog">
        Add product
      </Button>
      <LookupDialog<Product>
        open={open}
        onOpenChange={setOpen}
        title="Add a product"
        description="Search by name or SKU. Adding a product that is already on the sale adds one more."
        placeholder="Name or SKU"
        load={async (q) => (await apiGet<Page<Product>>("/inventory/", { q, active: true, limit: 20 })).items}
        keyOf={(p) => p.id}
        render={(p) => (
          <span className="flex items-baseline justify-between gap-3">
            <span className="flex flex-col">
              <span className="font-medium">{p.name}</span>
              <span className="font-mono text-ui-xs text-fg-muted">{p.sku}</span>
            </span>
            <span className="flex flex-col items-end text-ui-xs text-fg-muted">
              <span className="font-mono tabular-nums text-ui-sm text-fg">{formatMoney(p.price)}</span>
              <span>{p.qty_on_hand} in stock</span>
            </span>
          </span>
        )}
        onSelect={onPick}
        emptyMessage="No product matches. Check the spelling or add it in Products."
      />
    </>
  );
}
