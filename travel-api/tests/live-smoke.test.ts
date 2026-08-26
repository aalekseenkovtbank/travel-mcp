import assert from "node:assert/strict";
import { it } from "node:test";

import type { TripBrief, TripRunSnapshot } from "@travel-growth-inspiration/contracts";

import { createRuntime } from "../src/runtime.js";

const enabled = process.env.RUN_LIVE_SMOKE === "1";

it(
  "runs the opt-in read-only Saint Petersburg to Moscow chain",
  { skip: !enabled, timeout: 180_000 },
  async () => {
    const startDate = process.env.LIVE_SMOKE_START_DATE;
    const endDate = process.env.LIVE_SMOKE_END_DATE;
    assert.ok(startDate && endDate, "LIVE_SMOKE_START_DATE and LIVE_SMOKE_END_DATE are required");
    const brief: TripBrief = {
      preset: "weekend",
      originCityId: "saint-petersburg",
      destinationCityId: "moscow",
      travelers: { adults: 1, childrenAges: [] },
      time: { mode: "exact", startDate, endDate },
      interests: ["гастрономия", "концерты"],
    };
    const runtime = createRuntime({ databasePath: ":memory:", mode: "live" });
    try {
      const accepted = runtime.agent.createRun(brief);
      let snapshot: TripRunSnapshot | undefined;
      for (let attempt = 0; attempt < 600; attempt += 1) {
        snapshot = runtime.store.getRun(accepted.runId!);
        if (snapshot?.status === "completed" || snapshot?.status === "failed") break;
        await new Promise((resolve) => setTimeout(resolve, 250));
      }
      assert.ok(snapshot, "Live run snapshot was not created");
      if (snapshot.status === "failed") {
        assert.ok(snapshot.warnings.length, "A failed live run must explain the unavailable source");
        return;
      }
      assert.ok(snapshot.trips.length > 0 && snapshot.trips.length <= 3);
      assert.equal(snapshot.dataMode, "real");
      assert.ok(
        snapshot.trips.every((trip) =>
          [...trip.priceBreakdown.map((item) => item.price.source), ...trip.sources.map((item) => item.source)]
            .every((source) => !/демо/u.test(source)),
        ),
      );
    } finally {
      await runtime.close();
    }
  },
);

