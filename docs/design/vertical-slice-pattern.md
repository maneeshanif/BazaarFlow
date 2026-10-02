# Vertical slice pattern: copy this for every new module

The customers API (`/api/v1/customers/`, PRD F-009) is the reference slice. Every later module (products, orders,
vendors, campaigns, ...) follows the same shape, layer by layer. Files to open side by side:

| Layer | Reference file | What it must do |
| --- | --- | --- |
| Model | `app/models/customer.py` | `BaseModelMixin` + `TenantMixin` (+ `SoftDeleteMixin` for catalog and party tables); per-tenant unique **partial** index; money as `Numeric(14, 2)`; `version` column and `version_id_col` if two writers can touch a row |
| Migration | `alembic/versions/*` | Autogenerate, then add `ENABLE` + `FORCE` row level security and the `tenant_isolation` policy for the new table in the **same** migration; round-trip must pass (`verify.sh --slow --lane api-db`) |
| Schema | `app/schemas/customer.py` | `*Create` never contains `tenant_id`; limits equal the column sizes (a 422, never a database error); money is `Decimal`; ids are `UUID` |
| CRUD | `app/crud/crud_customer.py` | Every function takes `tenant_id` and filters on it (defense in depth on top of RLS); filters live rows with `live(Model)`; flushes, never commits |
| Controller | `app/api/controllers/customers_controller.py` | One role gate per route (`require_role(...)`), `Depends(get_tenant_db, scope="function")`, audit row for every write (`record_audit`), `409` for duplicates and races, `404` for unknown or foreign ids |
| Router | `app/api/routers/customers_router.py` + `routers/v1/__init__.py` | Mount under `/api/v1/<plural-noun>` |
| Tests | `tests/pg/test_customers_api.py`, `tests/pg/test_data_rules.py` | Tenant isolation through the API, role matrix, per-tenant uniqueness, soft delete, audit |

## Rules that make the slice safe (all enforced by tests)
1. The tenant comes from the verified token (`Principal`), never from the request body or the URL.
2. Every table has `tenant_id`, forced RLS and a policy; the API role cannot bypass RLS (`tests/pg/test_schema_rules.py`).
3. Every route carries an explicit authorization decision (`tests/architecture/test_authorization.py`).
4. Any route using the tenant session closes it before the response is sent (`tests/architecture/test_tenant_db_scope.py`).
5. Data conventions of PRD §12.2 hold for the new table (`tests/architecture/test_data_conventions.py`).
6. Writes that an agent proposes go through `app/services/approvals.py`, never straight to the table.

## Checklist for a new module
1. `/architect` the task: acceptance tests first, from the PRD section it implements.
2. Write the failing tests (tenant isolation, roles, audit, the module's own rules).
3. Model, migration (with RLS), schema, CRUD, controller, router, in that order.
4. `bash scripts/verify.sh --slow` until green, then `/review`.
5. Add the module's audited actions to `tests/pg/test_audit_actions.py` (and remove them from `NOT_YET_BUILT`).
6. Tick the task in `context/progress-tracker.md` and log it in `context/progress-log.md`.
