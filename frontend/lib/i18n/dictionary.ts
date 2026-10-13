/**
 * Urdu strings for the core screens (PRD §16, Q-004). The dictionary is keyed by the English text itself, so a screen
 * keeps working in English when a string has no entry: a missing key falls back to the English original, never to a
 * blank or a key name.
 *
 * Covered: the shell and navigation, sign-in and sign-up, the dashboard, sales, inventory, customers, orders and
 * approvals, plus the shared table, status and button words. Other screens stay in English until they are added here.
 * These translations were written by the assistant and need a native reader's review before launch.
 */

export type Locale = "en" | "ur";

export const LOCALES: readonly Locale[] = ["en", "ur"];

export const LOCALE_LABEL: Record<Locale, string> = { en: "English", ur: "اردو" };

/** Urdu is written right to left. */
export function dirFor(locale: Locale): "ltr" | "rtl" {
  return locale === "ur" ? "rtl" : "ltr";
}

const UR: Record<string, string> = {
  // shell
  "Skip to content": "مواد پر جائیں",
  "Main navigation": "مرکزی نیویگیشن",
  "Drawer navigation": "نیویگیشن",
  "Open navigation": "نیویگیشن کھولیں",
  "Primary tabs": "اہم ٹیبز",
  Search: "تلاش",
  Notifications: "اطلاعات",
  "Sign out": "سائن آؤٹ",
  Soon: "جلد",
  Language: "زبان",
  // navigation groups
  Overview: "جائزہ",
  Inbox: "ان باکس",
  Sales: "فروخت",
  Inventory: "انوینٹری",
  Finance: "مالیات",
  Marketing: "مارکیٹنگ",
  Voice: "آواز",
  Automations: "آٹومیشن",
  Settings: "سیٹنگز",
  Platform: "پلیٹ فارم",
  // navigation items
  Home: "ہوم",
  "Agent command center": "ایجنٹ کمانڈ سینٹر",
  "Agent activity": "ایجنٹ کی سرگرمی",
  Approvals: "منظوریاں",
  Conversations: "گفتگو",
  "Support calls": "سپورٹ کالز",
  "Sales chat": "سیلز چیٹ",
  "New sale": "نئی فروخت",
  Orders: "آرڈرز",
  Customers: "گاہک",
  Products: "مصنوعات",
  "Stock movements": "اسٹاک کی نقل و حرکت",
  Vendors: "وینڈرز",
  "Purchase orders": "خریداری کے آرڈر",
  "Finance overview": "مالیات کا جائزہ",
  "Finance dashboard": "مالیات ڈیش بورڈ",
  Studio: "اسٹوڈیو",
  Schedule: "شیڈول",
  Activity: "سرگرمی",
  Insights: "بصیرت",
  Comments: "تبصرے",
  "Call log": "کال لاگ",
  Recipes: "ترکیبیں",
  "Shop profile": "دکان کا پروفائل",
  Team: "ٹیم",
  Integrations: "انضمام",
  "Setup guide": "سیٹ اپ گائیڈ",
  Stock: "اسٹاک",
  More: "مزید",
  // page titles and descriptions
  "How the shop is doing.": "دکان کیسی چل رہی ہے۔",
  "Every sale you have posted.": "آپ کی ہر پوسٹ کی گئی فروخت۔",
  "What you sell, what is on the shelf, and what to reorder.": "آپ کیا بیچتے ہیں، شیلف پر کیا ہے، اور کیا دوبارہ منگوانا ہے۔",
  "Who buys from you, and who owes you.": "آپ سے کون خریدتا ہے، اور کس کے ذمے رقم ہے۔",
  "What the AI assistant wants to do. Nothing changes until you approve it.": "اے آئی اسسٹنٹ کیا کرنا چاہتا ہے۔ آپ کی منظوری تک کچھ نہیں بدلتا۔",
  "Record sales and ask questions by chat. Changes wait for approval.": "چیٹ کے ذریعے فروخت درج کریں اور سوال پوچھیں۔ تبدیلیاں منظوری کا انتظار کرتی ہیں۔",
  "Who you buy stock from, and what you owe them.": "آپ اسٹاک کس سے خریدتے ہیں، اور ان کے کتنے پیسے دینے ہیں۔",
  "Add a product": "مصنوع شامل کریں",
  "Find a customer": "گاہک تلاش کریں",
  "Add vendor": "وینڈر شامل کریں",
  // forms
  "Sign in": "سائن اِن",
  "Create account": "اکاؤنٹ بنائیں",
  "Create your shop": "اپنی دکان بنائیں",
  Email: "ای میل",
  Password: "پاس ورڈ",
  Shop: "دکان",
  "Shop name": "دکان کا نام",
  "Your name": "آپ کا نام",
  Phone: "فون",
  City: "شہر",
  Name: "نام",
  // buttons
  Save: "محفوظ کریں",
  Cancel: "منسوخ کریں",
  Approve: "منظور کریں",
  Reject: "مسترد کریں",
  Retry: "دوبارہ کوشش کریں",
  Skip: "چھوڑ دیں",
  Previous: "پچھلا",
  Next: "اگلا",
  "Clear filters": "فلٹر ہٹائیں",
  Show: "دکھائیں",
  // table headers and states
  Status: "حالت",
  Total: "کل",
  Balance: "بقایا",
  Date: "تاریخ",
  Price: "قیمت",
  Quantity: "مقدار",
  Customer: "گاہک",
  Product: "مصنوع",
  Items: "اشیاء",
  Vendor: "وینڈر",
  Created: "بنایا گیا",
  "You owe": "آپ کے ذمے",
  Payables: "واجبات",
  "Nothing here yet.": "ابھی یہاں کچھ نہیں ہے۔",
  "Could not load this list.": "فہرست لوڈ نہیں ہو سکی۔",
  // statuses
  posted: "پوسٹ ہو گیا",
  pending: "زیر التواء",
  approved: "منظور",
  rejected: "مسترد",
  executed: "مکمل",
  failed: "ناکام",
  expired: "میعاد ختم",
  paid: "ادا شدہ",
  owes: "بقایا ہے",
  settled: "ادائیگی مکمل",
  queued: "قطار میں",
  published: "شائع شدہ",
  cancelled: "منسوخ",
  drafted: "مسودہ",
  proposed: "تجویز کردہ",
  sent: "بھیج دیا",
  skipped: "چھوڑ دیا",
  connected: "منسلک",
  "low stock": "کم اسٹاک",
  "in stock": "اسٹاک میں",
  "out of stock": "اسٹاک ختم",
};

/** The text in the chosen language, or the English original when there is no translation. */
export function translate(locale: Locale, text: string): string {
  if (locale === "en") return text;
  return UR[text] ?? UR[text.toLowerCase()] ?? text;
}

export function isLocale(value: unknown): value is Locale {
  return value === "en" || value === "ur";
}
