"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { ErrorState, UnauthorizedState } from "@/components/app/StateViews";
import { ProductForm } from "@/components/inventory/ProductForm";
import { StockPanel } from "@/components/inventory/StockPanel";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { Product } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";

/** One product: edit its details (managers) and change its stock. Staff can view the stock level. */
export default function ProductPage() {
  const { id } = useParams<{ id: string }>();
  const { role } = useAuth();
  const [override, setOverride] = useState<Product | null>(null);
  const loaded = useLoad(() => apiGet<Product>(`/inventory/${id}`), [id]);

  if (loaded.state === "loading") {
    return (
      <div role="status" aria-busy="true" aria-label="Loading product" className="flex max-w-form flex-col gap-3">
        <Skeleton className="h-6 w-56" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }
  if (loaded.state === "unauthorized") return <UnauthorizedState />;
  if (loaded.state === "error" || !loaded.data) {
    const notFound = loaded.error?.status === 404;
    return <ErrorState message={notFound ? "That product does not exist or was deleted." : (loaded.error?.message ?? "Could not load this product.")} onRetry={notFound ? undefined : loaded.reload} />;
  }

  const product = override ?? loaded.data;
  const canManage = role === "owner" || role === "manager";
  if (!canManage) {
    return (
      <div className="max-w-form">
        <h1 className="text-ui-lg font-semibold text-fg">{product.name}</h1>
        <p className="mt-1 text-ui-sm text-fg-muted">
          {product.sku} &middot; {product.qty_on_hand} in stock. Ask a manager to change this product.
        </p>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-8">
      <ProductForm key={product.updated_at} product={product} onSaved={setOverride} />
      <StockPanel product={product} onChanged={setOverride} />
    </div>
  );
}
