# Load tests (k6)

`stack.k6.js` drives auth, role checks and tenant-scoped customers with virtual users and fails if
any auth/role/tenant answer is wrong or p95 latency exceeds budget.

Install k6 (`winget install k6`), start the stack (for example the Docker stack from
`scripts/e2e_auth_stack.py`, which seeds owner/manager/staff users), then:

    k6 run -e PROFILE=smoke  tests/load/stack.k6.js
    k6 run                   tests/load/stack.k6.js   # 10 users for 3 minutes
    k6 run -e PROFILE=stress tests/load/stack.k6.js   # ramps to 100 users

Never point it at the production API. The API has a per-IP limit of 120 requests/minute, so a
single k6 machine will see 429s above a few users; they are counted in `rate_limited_429`, not
treated as failures.
