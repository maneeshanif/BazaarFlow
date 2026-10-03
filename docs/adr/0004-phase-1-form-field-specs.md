# ADR 0004: Field specifications for the Phase 1 forms the PRD left open

Status: accepted by the owner's batch plan (2026-10-03). PRD §5.4 says the fields of forms without a §5.3 table are
"specified when their phase starts and recorded here before implementation (change control §25)". This ADR records them.
Every field below comes from the PRD data model (§12.3) or an existing model; none is a new business field.

## F-009 Customers and udhaar ledger

| Field | Type | Required | Validation / rule | Notes |
| --- | --- | --- | --- | --- |
| phone | phone | yes | 7-20 digits, optional leading +; unique per tenant among live customers | the form accepts 0300... and stores +92300... |
| name | text | no | at most 255 characters | blank is stored as empty |
| email | email | no | valid address, at most 254 characters | |
| address | text | no | at most 512 characters | |
| balance | money, read-only | system | debits minus credits of the customer's ledger entries | hidden from staff |

Payment (settling udhaar): `amount` money greater than 0 and at most the balance; `method` cash, card, bank or wallet.
A payment writes one `payments` row and one ledger credit in one transaction. A customer who owes money cannot be
deleted. Roles: owner and manager open the screen; staff can look customers up and add one while selling but never see
balances; only the owner deletes (PRD §14.2).

## F-007 New sale (the field table in PRD 5.3 is unchanged; these are the rules the build settled)

- Lines: 1 to 100; quantity a whole number from 1 to 1,000,000; `unit_price` defaults to the product's current price and may be changed per line; the same product on two lines is checked against stock together.
- `discount` from 0 to the items total. `payment_method` cash, card, bank, wallet or udhaar. `amount_paid` defaults to the total; the unpaid part goes on the customer's udhaar and needs a customer. A sale paid by "udhaar" has nothing paid now.
- Stock: a sale never takes stock below zero. A manager or owner may "sell more than the shelf count"; the shelf count is first corrected by a recorded adjustment (audited as `order.stock_override`), then the sale takes it to zero.
- The channel is set by the source (`pos` for this form) and is never taken from the request. A retried request with the same `Idempotency-Key` returns the sale it already made.
- Prices, cost and product name are copied onto the line. Totals and every figure on the form come from the server (`POST /sales/preview`); the browser adds nothing up.

## F-008 Orders list and detail

List fields: reference (first 8 characters of the id), when, customer or walk-in, item count, total, still owed (udhaar), status. Filters: status, search over customer, product and note; sorts: newest, oldest, biggest. Detail adds the lines (cost visible to manager and owner only), payments, notes and totals.
Reversing a posted sale (manager or owner) needs a reason of 3 to 255 characters. It returns the stock (movement reason `reversal`), marks the payments reversed and credits the customer's ledger by what the sale had put on credit. If the customer had already paid part of that credit the balance goes negative, meaning the shop owes them. A sale can be reversed once. Posted sales have no edit or delete.

## F-019 Team and roles

| Field | Type | Required | Validation / rule | Notes |
| --- | --- | --- | --- | --- |
| name | text | yes | 2 to 80 characters | |
| email | email | yes | valid, at most 254 characters, unique per person | existing accounts are added to the shop and keep their password |
| role | select | yes | manager or staff | owners are never added or changed here |
| password | password | for a new person | at least 8 characters, not in the common-password list | given to them by the owner; ignored for an existing account |

Rules: owner only; a person is in a shop once; the owner cannot be changed or removed; a role change applies from the person's next request; removing a person ends their sessions in that shop immediately. Adding, changing and removing are audited (`team.added`, `team.role_changed`, `team.removed`) without the password. E-mail invitations need an e-mail provider and are a Phase 2 item.
