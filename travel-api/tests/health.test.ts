import assert from "node:assert/strict";
import { describe, it } from "node:test";

import request from "supertest";

import { createApp } from "../src/app.js";

describe("Travel Nova API", () => {
  it("reports its health", async () => {
    const response = await request(createApp()).get("/api/v1/health").expect(200);

    assert.equal(response.body.status, "ok");
    assert.equal(response.body.service, "travel-nova-api");
    const requestId = response.headers["x-request-id"];
    assert.equal(typeof requestId, "string");
    assert.match(requestId ?? "", /^[0-9a-f-]{36}$/);
  });

  it("preserves a caller request id", async () => {
    const response = await request(createApp())
      .get("/health")
      .set("x-request-id", "travel-test-123")
      .expect(200);

    assert.equal(response.headers["x-request-id"], "travel-test-123");
  });

  it("returns a structured 404", async () => {
    const response = await request(createApp()).get("/missing").expect(404);

    assert.equal(response.body.error.code, "ROUTE_NOT_FOUND");
    assert.equal(typeof response.body.requestId, "string");
  });
});
