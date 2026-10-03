// k6 load test for the BazaarFlow API (Phase 0 surface: auth, roles, tenant-scoped customers).
//
//   k6 run -e BASE_URL=http://localhost:8000 -e OWNER_EMAIL=... -e MANAGER_EMAIL=... -e STAFF_EMAIL=... \
//          -e PASSWORD=... tests/load/stack.k6.js
//   Add -e PROFILE=smoke for a 1-VU sanity run, PROFILE=stress to push past the expected load.
//
// Run it against a LOCAL or throwaway stack, never the production API: it creates customers and
// trips rate limits on purpose. Logins happen once in setup() (login attempts are throttled and
// audited), then every virtual user reuses the role tokens.
import http from "k6/http";
import { check, group, sleep } from "k6";
import { Counter, Rate } from "k6/metrics";

const BASE = __ENV.BASE_URL || "http://localhost:8000";
const API = `${BASE}/api/v1`;
const PASSWORD = __ENV.PASSWORD || "e2e-password-1";
const USERS = {
  owner: __ENV.OWNER_EMAIL || "owner@example.com",
  manager: __ENV.MANAGER_EMAIL || "manager@example.com",
  staff: __ENV.STAFF_EMAIL || "staff@example.com",
};

const rateLimited = new Counter("rate_limited_429");
const wrongAnswers = new Rate("wrong_answers"); // auth/role/tenant decisions that came out wrong
const PROFILES = {
  smoke: { stages: [{ duration: "20s", target: 1 }] },
  load: {
    stages: [
      { duration: "30s", target: 10 },
      { duration: "2m", target: 10 },
      { duration: "30s", target: 0 },
    ],
  },
  stress: {
    stages: [
      { duration: "30s", target: 20 },
      { duration: "1m", target: 50 },
      { duration: "1m", target: 100 },
      { duration: "30s", target: 0 },
    ],
  },
};

export const options = {
  ...(PROFILES[__ENV.PROFILE || "load"]),
  thresholds: {
    // Correctness must hold under load; latency budgets are the PRD-style "feels instant" targets.
    wrong_answers: ["rate==0"],
    http_req_failed: ["rate<0.05"],
    "http_req_duration{kind:read}": ["p(95)<800"],
    "http_req_duration{kind:write}": ["p(95)<1500"],
  },
};

const json = { "Content-Type": "application/json" };
const auth = (t) => ({ headers: { ...json, Authorization: `Bearer ${t}` } });

export function setup() {
  const tokens = {};
  for (const [role, email] of Object.entries(USERS)) {
    const r = http.post(`${API}/auth/login`, JSON.stringify({ email, password: PASSWORD }), { headers: json });
    if (r.status !== 200) {
      throw new Error(`login failed for ${role} (${r.status}): is the stack up and the seed password right?`);
    }
    tokens[role] = r.json("access_token");
  }
  return tokens;
}

export default function (tokens) {
  group("health and public", () => {
    const r = http.get(`${BASE}/health`, { tags: { kind: "read" } });
    check(r, { "health 200": (x) => x.status === 200 });
  });

  group("auth decisions", () => {
    const anon = http.get(`${API}/auth/me`, { tags: { kind: "read" } });
    wrongAnswers.add(anon.status !== 401 && anon.status !== 429);

    const bad = http.post(`${API}/auth/login`, JSON.stringify({ email: USERS.owner, password: "definitely-wrong" }), {
      headers: json,
      tags: { kind: "read" },
    });
    // 401 = wrong password refused; 429 = throttled. Anything else means the gate failed.
    wrongAnswers.add(bad.status !== 401 && bad.status !== 429);

    const me = http.get(`${API}/auth/me`, { ...auth(tokens.staff), tags: { kind: "read" } });
    if (me.status === 429) rateLimited.add(1);
    else wrongAnswers.add(me.status !== 200);
  });

  group("tenant-scoped customers", () => {
    const list = http.get(`${API}/customers/`, { ...auth(tokens.staff), tags: { kind: "read" } });
    if (list.status === 429) rateLimited.add(1);
    else wrongAnswers.add(list.status !== 200);

    const phone = `03${String(Math.floor(Math.random() * 1e9)).padStart(9, "0")}`;
    const body = JSON.stringify({ name: `k6 ${__VU}-${__ITER}`, phone });
    const create = http.post(`${API}/customers/`, body, { ...auth(tokens.manager), tags: { kind: "write" } });
    if (create.status === 429) rateLimited.add(1);
    else wrongAnswers.add(![201, 409, 422].includes(create.status)); // 409/422 = valid refusal of a duplicate/odd phone

    // No token at all must never reach tenant data.
    const open = http.get(`${API}/customers/`, { tags: { kind: "read" } });
    wrongAnswers.add(open.status !== 401 && open.status !== 429);
  });

  group("role boundary", () => {
    // Staff may not add stock: manager and above only.
    const r = http.patch(`${BASE}/api/inventory/K6-NOPE/add-stock`, JSON.stringify({ quantity: 1 }), {
      ...auth(tokens.staff),
      tags: { kind: "write" },
    });
    // Legacy JSON routes are off in production (404); locally the role check answers 403.
    wrongAnswers.add(![403, 404, 429].includes(r.status));
  });

  sleep(1);
}
