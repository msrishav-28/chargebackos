import assert from "node:assert/strict";
import { test } from "node:test";
import { loginSchema, staffSchema, disputeListSchema } from "./ops-schemas.ts";
import { validateQueueSearch } from "./queue-search.ts";

test("staff responses reject unknown roles and empty session tokens", () => {
  assert.equal(staffSchema.safeParse({ email: "staff@example.test", displayName: "Staff", role: "owner" }).success, false);
  assert.equal(loginSchema.safeParse({ token: "", user: { email: "staff@example.test", displayName: "Staff", role: "viewer" } }).success, false);
});

test("queue rejects missing totals and impossible pagination", () => {
  assert.equal(disputeListSchema.safeParse({ items: [], page: 1, limit: 50 }).success, false);
  assert.equal(disputeListSchema.safeParse({ items: [], total: 0, page: 0, limit: 50 }).success, false);
  assert.deepEqual(disputeListSchema.parse({ items: [], total: 0, page: 1, limit: 50 }).items, []);
});

test("queue search preserves page and filters and rejects unsafe page values", () => {
  assert.deepEqual(validateQueueSearch({ page: "3", q: "CB-DEMO-01", review: "1" }), {
    page: 3, q: "CB-DEMO-01", review: true, high: undefined, merchant: undefined,
    family: undefined, category: undefined, state: undefined,
  });
  for (const page of [0, -1, 1.5, Infinity, "invalid"]) assert.equal(validateQueueSearch({ page }).page, undefined);
});
