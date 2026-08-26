import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, it } from "node:test";

import type { TripBrief, TripRunSnapshot } from "@travel-growth-inspiration/contracts";
import request from "supertest";

import { createApp } from "../src/app.js";
import type { EditorialService } from "../src/modules/editorial/editorial-service.js";
import {
  nearbyPlaceKinds,
  targetEventCount,
  TripCompiler,
  tripDateWindows,
} from "../src/modules/planner/trip-compiler.js";
import { DemoPlannerProvider } from "../src/modules/providers/demo-planner-provider.js";
import {
  UnavailableWeatherService,
  type WeatherService,
} from "../src/modules/providers/open-meteo-weather-service.js";
import { TbankMcpClient } from "../src/modules/providers/tbank-mcp-client.js";
import { TravelStore } from "../src/modules/storage/travel-store.js";
import { createRuntime, readableMcpError, type AppRuntime, type RuntimeOptions } from "../src/runtime.js";

const exactBrief: TripBrief = {
  preset: "weekend",
  originCityId: "saint-petersburg",
  travelers: { adults: 1, childrenAges: [] },
  time: { mode: "exact", startDate: "2026-09-18", endDate: "2026-09-21" },
  interests: ["гастрономия", "концерты"],
};

const testEditorial: EditorialService = {
  decorate: async (proposals) => ({ proposals }),
  interpretChange: async (text) => ({
    action: text === "Сделай дешевле" ? "cheaper" : "general",
    instructions: text,
  }),
};

async function waitForRun(runtime: AppRuntime, runId: string): Promise<TripRunSnapshot> {
  for (let attempt = 0; attempt < 160; attempt += 1) {
    const run = runtime.store.getRun(runId);
    if (run?.status === "completed" || run?.status === "failed") return run;
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  throw new Error("Trip run did not finish in time");
}

function createTestRuntime(options: RuntimeOptions): AppRuntime {
  return createRuntime({
    ...options,
    editorial: testEditorial,
    weatherService: new UnavailableWeatherService(),
  });
}

describe("Trip compiler", () => {
  it("adjusts event density and nearby place themes to the interpreted preferences", () => {
    assert.equal(targetEventCount("2026-09-01", "2026-09-15", "relaxed"), 4);
    assert.equal(targetEventCount("2026-09-01", "2026-09-15", "balanced"), 5);
    assert.equal(targetEventCount("2026-09-01", "2026-09-15", "active"), 6);
    assert.deepEqual(nearbyPlaceKinds({
      ...exactBrief,
      interests: ["выставки"],
      preferences: {
        destinationTags: [{ value: "природа", polarity: "prefer", strength: "soft" }],
        activities: [{ value: "бары", polarity: "prefer", strength: "soft" }],
        other: [],
      },
    }), ["culture", "nature", "nightlife"]);
  });

  it("ranks cool destinations above hot ones for a hard temperature preference", async () => {
    const coolCities = new Set(["murmansk", "kaliningrad", "irkutsk"]);
    const weather: WeatherService = {
      forTrip: async (city, window) => ({
        data: {
          days: [{
            kind: "climate",
            date: window.startDate,
            temperatureMinC: coolCities.has(city.id) ? 11 : 22,
            temperatureMaxC: coolCities.has(city.id) ? 18 : 31,
            precipitationFrequencyPct: 25,
            sampleSize: 30,
          }],
        },
        warnings: [],
        available: true,
        source: "Тестовый климат",
        checkedAt: "2026-08-19T10:00:00.000Z",
      }),
    };
    const provider = new DemoPlannerProvider();
    const profile = (await provider.profile()).data;
    const compiler = new TripCompiler(provider, testEditorial, weather);
    const result = await compiler.compile("run-climate", {
      ...exactBrief,
      preferences: {
        destinationTags: [],
        activities: [],
        climate: { maxDayTemperatureC: 20, strength: "hard" },
        other: [],
      },
    }, profile);

    assert.equal(result.proposals.length, 3);
    assert.ok(result.proposals.every((proposal) => coolCities.has(proposal.destination.id)));
    assert.ok(result.proposals.every((proposal) =>
      proposal.fitReasons.some((reason) => reason.includes("18 °C"))));
    assert.doesNotMatch(result.warnings.join(" "), /меньше трёх направлений/u);
  });

  it("warns when a hard climate constraint has to be relaxed", async () => {
    const weather: WeatherService = {
      forTrip: async (city, window) => ({
        data: {
          days: [{
            kind: "climate",
            date: window.startDate,
            temperatureMinC: city.id === "murmansk" ? 10 : 21,
            temperatureMaxC: city.id === "murmansk" ? 17 : 30,
            precipitationFrequencyPct: 25,
            sampleSize: 30,
          }],
        },
        warnings: [],
        available: true,
        source: "Тестовый климат",
        checkedAt: "2026-08-19T10:00:00.000Z",
      }),
    };
    const provider = new DemoPlannerProvider();
    const compiler = new TripCompiler(provider, testEditorial, weather);
    const result = await compiler.compile("run-relaxed-climate", {
      ...exactBrief,
      preferences: {
        destinationTags: [],
        activities: [],
        climate: { maxDayTemperatureC: 20, strength: "hard" },
        other: [],
      },
    }, (await provider.profile()).data);

    assert.equal(result.proposals.length, 3);
    assert.match(result.warnings.join(" "), /меньше трёх направлений/u);
  });

  it("creates at most three date windows and preserves duration", () => {
    const windows = tripDateWindows({
      ...exactBrief,
      time: {
        mode: "flexible",
        windowStart: "2026-09-01",
        windowEnd: "2026-09-30",
        nights: 4,
      },
    });
    assert.equal(windows.length, 3);
    for (const window of windows) {
      assert.equal(
        Math.round((Date.parse(window.endDate) - Date.parse(window.startDate)) / 86_400_000),
        4,
      );
    }
  });

  it("returns three different destinations without a fixed city", async () => {
    const runtime = createTestRuntime({ databasePath: ":memory:", mode: "demo", llmProxyApiKey: "" });
    try {
      const accepted = runtime.agent.createRun(exactBrief);
      const run = await waitForRun(runtime, accepted.runId!);
      assert.equal(run.status, "completed");
      assert.equal(run.trips.length, 3);
      assert.equal(new Set(run.trips.map((trip) => trip.destination.id)).size, 3);
      assert.deepEqual(run.trips.map((trip) => trip.tier), [
        "cohort_floor",
        "cohort_typical",
        "cohort_ceiling",
      ]);
    } finally {
      await runtime.close();
    }
  });

  it("creates three Saint Petersburg variants when the destination is fixed", async () => {
    const runtime = createTestRuntime({ databasePath: ":memory:", mode: "demo", llmProxyApiKey: "" });
    try {
      const accepted = runtime.agent.createRun({
        ...exactBrief,
        originCityId: "moscow",
        destinationCityId: "saint-petersburg",
      });
      const run = await waitForRun(runtime, accepted.runId!);
      assert.equal(run.trips.length, 3);
      assert.ok(run.trips.every((trip) => trip.destination.id === "saint-petersburg"));
      assert.equal(new Set(run.trips.map((trip) => trip.hotel.hotelId)).size > 1, true);
    } finally {
      await runtime.close();
    }
  });

  it("marks the closest over-budget option instead of silently exceeding", async () => {
    const runtime = createTestRuntime({ databasePath: ":memory:", mode: "demo", llmProxyApiKey: "" });
    try {
      const accepted = runtime.agent.createRun({ ...exactBrief, budgetRub: 5_000 });
      const run = await waitForRun(runtime, accepted.runId!);
      assert.equal(run.trips.length, 1);
      assert.equal(run.trips[0]?.tier, "closest_over_budget");
      assert.match(run.warnings.join(" "), /ближайший вариант выше лимита/u);
    } finally {
      await runtime.close();
    }
  });
});

describe("Planner API and persistence", () => {
  it("publishes catalog, run snapshots and stored SSE events", async () => {
    const runtime = createTestRuntime({ databasePath: ":memory:", mode: "demo", llmProxyApiKey: "" });
    const app = createApp(runtime);
    try {
      const catalog = await request(app).get("/api/v1/catalog/cities").expect(200);
      assert.equal(catalog.body.cities.length, 20);
      const readiness = await request(app).get("/api/v1/system/readiness").expect(200);
      assert.equal(readiness.body.dataMode, "demo");
      assert.equal(readiness.body.status, "ready");
      const accepted = await request(app).post("/api/v1/trip-runs").send(exactBrief).expect(202);
      const run = await waitForRun(runtime, accepted.body.runId);
      const snapshot = await request(app).get(`/api/v1/trip-runs/${run.id}`).expect(200);
      assert.equal(snapshot.body.trips.length, 3);
      assert.equal(snapshot.body.dataMode, "demo");
      assert.ok(["complete", "partial"].includes(snapshot.body.completeness));
      const events = runtime.store.getEvents(accepted.body.jobId);
      assert.equal(events[0]?.type, "job.started");
      assert.equal(events.at(-1)?.type, "job.completed");
      assert.ok(events.some((event) => event.type === "trip.partial" && event.data.stage === "core"));
      assert.ok(events.some((event) => event.type === "trip.ready" && event.data.stage === "enriched"));
      const trip = runtime.store.getTrip(run.trips[0]!.id)!;
      assert.equal(trip.preparationStatus, "ready");
      assert.equal(trip.revisionCount, 1);
    } finally {
      await runtime.close();
    }
  });

  it("persists chat and creates an immutable trip revision", async () => {
    const runtime = createTestRuntime({ databasePath: ":memory:", mode: "demo", llmProxyApiKey: "" });
    const app = createApp(runtime);
    try {
      const accepted = runtime.agent.createRun({ ...exactBrief, destinationCityId: "kazan" });
      const run = await waitForRun(runtime, accepted.runId!);
      const trip = runtime.store.getTrip(run.trips[0]!.id)!;
      const messageResponse = await request(app)
        .post(`/api/v1/trips/${trip.id}/messages`)
        .send({ text: "Сделай дешевле", baseRevisionId: trip.latestRevision.id })
        .expect(202);
      for (let attempt = 0; attempt < 160; attempt += 1) {
        const job = runtime.store.getJob(messageResponse.body.jobId);
        if (job?.status === "completed" || job?.status === "failed") break;
        await new Promise((resolve) => setTimeout(resolve, 20));
      }
      const updated = runtime.store.getTrip(trip.id)!;
      assert.equal(updated.revisionCount, 2);
      assert.equal(runtime.store.getMessages(trip.id).length, 2);
      assert.notEqual(updated.latestRevision.id, trip.latestRevision.id);
      assert.ok(updated.latestRevision.changeSummary?.length);
    } finally {
      await runtime.close();
    }
  });

  it("marks queued work as interrupted after restart", () => {
    const directory = mkdtempSync(path.join(tmpdir(), "travel-nova-interrupted-"));
    const databasePath = path.join(directory, "planner.sqlite");
    const store = new TravelStore(databasePath);
    const runId = store.createRun(exactBrief, "real");
    const jobId = store.createJob("compile", { runId });
    store.close();
    const reopened = new TravelStore(databasePath);
    try {
      assert.equal(reopened.getJob(jobId)?.status, "interrupted");
      assert.equal(reopened.getRun(runId)?.status, "failed");
      assert.match(reopened.getRun(runId)?.warnings.join(" ") ?? "", /перезапуск/u);
    } finally {
      reopened.close();
      rmSync(directory, { recursive: true, force: true });
    }
  });

  it("restores a completed run from SQLite", async () => {
    const directory = mkdtempSync(path.join(tmpdir(), "travel-nova-test-"));
    const databasePath = path.join(directory, "planner.sqlite");
    const runtime = createTestRuntime({ databasePath, mode: "demo", llmProxyApiKey: "" });
    let runId = "";
    try {
      const accepted = runtime.agent.createRun(exactBrief);
      runId = accepted.runId!;
      const run = await waitForRun(runtime, runId);
      assert.equal(run.status, "completed");
    } finally {
      await runtime.close();
    }
    const reopened = new TravelStore(databasePath);
    try {
      assert.equal(reopened.getRun(runId)?.trips.length, 3);
    } finally {
      reopened.close();
      rmSync(directory, { recursive: true, force: true });
    }
  });
});

describe("Safety boundary", () => {
  it("turns an MCP protocol timeout into a user-facing readiness message", () => {
    assert.equal(
      readableMcpError("MCP error -32001: Request timed out"),
      "T-Bank MCP не ответил вовремя; реальный контур временно недоступен",
    );
  });

  it("rejects money tools before starting MCP", async () => {
    const client = new TbankMcpClient("/definitely/not/started", 1000);
    await assert.rejects(() => client.call("transfer", { amount: 1 }), /read-only allowlist/u);
  });
});
