import type { components } from "@/lib/api/schema";

/** Request/response shapes come from the generated client (contracts/openapi.json); never hand-write them. */
type Schemas = components["schemas"];

export type Product = Schemas["ProductOut"];
export type ProductCreate = Schemas["ProductCreate"];
export type ProductUpdate = Schemas["ProductUpdate"];
export type StockMovement = Schemas["StockMovementOut"];
export type StockMovementCreate = Schemas["StockMovementCreate"];

export type Customer = Schemas["CustomerOut"];
export type CustomerCreate = Schemas["CustomerCreate"];
export type CustomerUpdate = Schemas["CustomerUpdate"];
export type LedgerEntry = Schemas["LedgerEntryOut"];
export type Payment = Schemas["PaymentOut"];

export type Page<T> = { items: T[]; total: number; next_cursor: string | null };
