/**
 * The single formatting module (PRD §16, ui-rules.md "Formatting"). Money, numbers and dates are formatted here and
 * nowhere else: never call toLocaleString or Intl inline in a component.
 *
 * Defaults are the shop defaults for a Pakistani retailer (PKR, Asia/Karachi); a tenant's own configuration is
 * passed in as options once tenant settings reach the frontend.
 */

export const DEFAULT_CURRENCY = "PKR";
export const DEFAULT_TIMEZONE = "Asia/Karachi";

const CURRENCY_SYMBOL: Record<string, string> = { PKR: "Rs", USD: "$", EUR: "€", GBP: "£", INR: "₹" };

type MoneyOptions = {
  currency?: string;
  /** "sign" -> -Rs 500, "parentheses" -> (Rs 500) as in financial reports. */
  negative?: "sign" | "parentheses";
};

const toNumber = (value: number | string): number => (typeof value === "number" ? value : Number(value));

/** Round to cents so that binary floating point noise (0.1 + 0.2) never reaches the screen. */
const toCents = (n: number): number => Math.round((Math.abs(n) + Number.EPSILON) * 100) / 100;

export function formatNumber(value: number | string | null | undefined, opts: { precision?: number } = {}): string {
  if (value === null || value === undefined || value === "") return "-";
  const n = toNumber(value);
  if (!Number.isFinite(n)) return "-";
  const precision = opts.precision ?? 0;
  return new Intl.NumberFormat("en-US", { minimumFractionDigits: precision, maximumFractionDigits: precision }).format(n);
}

export function formatMoney(value: number | string | null | undefined, opts: MoneyOptions = {}): string {
  if (value === null || value === undefined || value === "") return "-";
  const n = toNumber(value);
  if (!Number.isFinite(n)) return "-";
  const currency = opts.currency ?? DEFAULT_CURRENCY;
  const symbol = CURRENCY_SYMBOL[currency] ?? currency;
  const abs = toCents(n);
  const body = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: Number.isInteger(abs) ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(abs);
  const text = `${symbol} ${body}`;
  if (n >= 0 || abs === 0) return text;
  return opts.negative === "parentheses" ? `(${text})` : `-${text}`;
}

type DateOptions = { timezone?: string };

function parts(iso: string | Date, timezone: string, withTime: boolean): Record<string, string> {
  const fmt = new Intl.DateTimeFormat("en-GB", {
    timeZone: timezone,
    day: "2-digit",
    month: "short",
    year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit", hourCycle: "h23" as const } : {}),
  });
  return Object.fromEntries(fmt.formatToParts(new Date(iso)).map((p) => [p.type, p.value]));
}

/** "02 Oct 2026". Timestamps are stored in UTC and shown in the shop's timezone. */
export function formatDate(iso: string | Date | null | undefined, opts: DateOptions = {}): string {
  if (!iso) return "-";
  const p = parts(iso, opts.timezone ?? DEFAULT_TIMEZONE, false);
  return `${p.day} ${p.month} ${p.year}`;
}

/** "02 Oct 2026, 01:30" */
export function formatDateTime(iso: string | Date | null | undefined, opts: DateOptions = {}): string {
  if (!iso) return "-";
  const p = parts(iso, opts.timezone ?? DEFAULT_TIMEZONE, true);
  return `${p.day} ${p.month} ${p.year}, ${p.hour}:${p.minute}`;
}
