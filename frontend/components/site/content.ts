/** Words shared by several public pages, kept in one place so the pages never disagree. */

export const CONTROLS = [
  "Sales, payments and stock changes wait for a manager or the owner to approve them.",
  "Every conversation is logged with the tools it used. Names, phone numbers and emails are hidden in the log.",
  "The owner can pause the assistant at any moment, and each shop has a monthly AI allowance that stops it.",
  "Staff can chat and propose. Only owners and managers approve.",
];

/** Where messages from the contact page go. Placeholder until the owner sets the real address. */
export const CONTACT_EMAIL = "hello@bazaarflow.example";

export const PUBLIC_MENU = [
  { label: "About", href: "/about" },
  { label: "How it works", href: "/how-it-works" },
  { label: "What it handles", href: "/features" },
  { label: "News", href: "/news" },
  { label: "Contact", href: "/contact" },
  { label: "Live demo", href: "/demo" },
];

/** The modules, as the PRD lists them (docs/prd/PRD.md section 5). `soon` marks what waits for outside accounts. */
export const MODULES: { key: string; name: string; tone: "coral" | "sunny" | "sky" | "indigo" | "orange" | "lime"; line: string; points: string[]; soon?: boolean }[] = [
  {
    key: "sales",
    name: "Sales",
    tone: "coral",
    line: "Say what you sold, in English or Roman Urdu.",
    points: ["A sales chat that drafts the order for you to approve", "A plain form for when you would rather type it", "Orders with a short reference, the customer, the money and a text status"],
  },
  {
    key: "khata",
    name: "Khata",
    tone: "indigo",
    line: "Every customer's purchases and payments in one place.",
    points: ["A ledger per customer with what they still owe", "Payments recorded the moment you say them", "Reversals that keep the history instead of erasing it"],
  },
  {
    key: "stock",
    name: "Stock",
    tone: "sunny",
    line: "What is on the shelf, what is low, what to reorder.",
    points: ["Products with stock levels and a reorder point", "Stock movements for every sale, return and correction", "Vendors, purchase orders and what you owe them"],
  },
  {
    key: "money",
    name: "Money",
    tone: "sky",
    line: "Today's sales, profit and the ledger behind them.",
    points: ["A home dashboard whose every figure links to its records", "Finance overview and ledger for owners", "Managers see sales without the margins"],
  },
  {
    key: "inbox",
    name: "Inbox",
    tone: "orange",
    line: "Customer messages next to the orders they are about.",
    points: ["A single inbox for customer conversations", "WhatsApp orders: coming next, once the shop's account is connected", "Support calls by voice assistant: being connected"],
    soon: true,
  },
  {
    key: "marketing",
    name: "Posts",
    tone: "lime",
    line: "An offer drafted in your tone, sent for approval.",
    points: ["A marketing studio that drafts posts and a schedule", "Activity and insights for what went out", "Publishing to Facebook: coming next, with your Page connected"],
    soon: true,
  },
];
