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

<!-- F-007 / F-008 / F-019 sections are appended as those tasks are built. -->
