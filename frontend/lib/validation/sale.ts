/**
 * Client-side checks for the New sale form (PRD F-007): what can be said without asking the server, so the person is
 * told at once. It does no money arithmetic (the server adds the sale up and decides again when it is posted).
 */

export type SaleLineInput = { qty: string; price: string; name: string };

export type SaleFormInput = {
  lines: SaleLineInput[];
  discount: string;
  paid: string;
  method: string;
  hasCustomer: boolean;
};

const WHOLE = /^[1-9]\d{0,6}$/;
const MONEY = /^\d{1,12}(\.\d{1,2})?$/;

/** Field key -> message. Keys: lines, line-<index>, customer, discount, paid. */
export function saleFormErrors(input: SaleFormInput): Record<string, string> {
  const errors: Record<string, string> = {};
  if (input.lines.length === 0) errors.lines = "Add at least one item to the sale";
  input.lines.forEach((line, i) => {
    if (!WHOLE.test(line.qty.trim())) errors[`line-${i}`] = `Quantity of ${line.name} must be a whole number above zero`;
    else if (!MONEY.test(line.price.trim())) errors[`line-${i}`] = `Price of ${line.name} must be an amount like 2500 or 2500.50`;
  });
  if (input.discount.trim() !== "" && !MONEY.test(input.discount.trim())) errors.discount = "Enter a discount like 100 or 100.50";
  if (input.method !== "udhaar" && input.paid.trim() !== "" && !MONEY.test(input.paid.trim())) errors.paid = "Enter the amount received like 500 or 500.50";
  const partlyOnCredit = input.method === "udhaar" || (input.paid.trim() !== "" && MONEY.test(input.paid.trim()));
  if (partlyOnCredit && !input.hasCustomer && input.method === "udhaar") errors.customer = "Choose the customer: a sale on credit needs to know who owes";
  return errors;
}
