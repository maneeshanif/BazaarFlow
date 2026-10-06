import type { components } from "@/lib/api/schema";

/** Request/response shapes come from the generated client (contracts/openapi.json); never hand-write them. */
type Schemas = components["schemas"];

export type Product = Schemas["ProductOut"];
export type ProductCreate = Schemas["ProductCreate"];
export type ProductUpdate = Schemas["ProductUpdate"];
export type StockMovement = Schemas["StockMovementOut"];
export type StockMovementListItem = Schemas["StockMovementListItem"];
export type StockMovementCreate = Schemas["StockMovementCreate"];

export type Customer = Schemas["CustomerOut"];
export type CustomerCreate = Schemas["CustomerCreate"];
export type CustomerUpdate = Schemas["CustomerUpdate"];
export type LedgerEntry = Schemas["LedgerEntryOut"];
export type Payment = Schemas["PaymentOut"];

export type SaleCreate = Schemas["SaleCreate"];
export type SalePreview = Schemas["SalePreview"];
export type OrderDetail = Schemas["OrderDetail"];
export type OrderSummary = Schemas["OrderSummary"];

export type TeamMember = Schemas["TeamMemberOut"];

export type ChatResponse = Schemas["ChatResponse"];
export type ChatAction = Schemas["ChatAction"];
export type Approval = Schemas["ApprovalOut"];
export type AgentRun = Schemas["AgentRunOut"];
export type AgentRunDetail = Schemas["AgentRunDetail"];
export type AgentStatus = Schemas["AgentStatus"];

export type Page<T> = { items: T[]; total: number; next_cursor: string | null };
export type MarketingPost = Schemas["PostOut"];
export type DraftBrief = Schemas["DraftRequest"];
export type Dashboard = Schemas["DashboardOut"];
export type DashboardRange = Dashboard["range"];

export type ShopVendor = Schemas["ShopVendorOut"];
export type VendorBill = Schemas["VendorBillOut"];
export type VendorPayment = Schemas["VendorPaymentOut"];
export type VendorLedgerEntry = Schemas["VendorLedgerEntryOut"];
export type PayableRow = Schemas["PayableRow"];
export type ShopSettings = Schemas["ShopSettingsOut"];
export type FinanceOverview = Schemas["FinanceOverview"];
export type CashBookEntry = Schemas["CashBookEntry"];
export type AgentDashboard = Schemas["AgentDashboard"];
