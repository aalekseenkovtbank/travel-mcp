import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { City } from "@travel-growth-inspiration/contracts";

import { OpenMeteoWeatherService } from "../src/modules/providers/open-meteo-weather-service.js";

const city: City = {
  id: "moscow",
  name: "Москва",
  iata: "MOW",
  latitude: 55.7558,
  longitude: 37.6176,
  tags: [],
  accent: "",
};

function weatherFetcher(counter: { forecast: number; archive: number }): typeof fetch {
  return (async (input: Parameters<typeof fetch>[0]) => {
    const url = new URL(String(input));
    if (url.hostname === "forecast.test") {
      counter.forecast += 1;
      return new Response(JSON.stringify({
        daily: {
          time: ["2026-09-01"],
          temperature_2m_min: [14.4],
          temperature_2m_max: [20.6],
          precipitation_probability_max: [61.2],
          weather_code: [63],
        },
      }), { status: 200, headers: { "content-type": "application/json" } });
    }
    counter.archive += 1;
    return new Response(JSON.stringify({
      daily: {
        time: ["1991-08-30", "2005-09-02", "2020-09-05"],
        temperature_2m_min: [10, 12, 14],
        temperature_2m_max: [20, 22, 24],
        precipitation_sum: [0, 1, 5],
      },
    }), { status: 200, headers: { "content-type": "application/json" } });
  }) as typeof fetch;
}

describe("Open-Meteo weather service", () => {
  it("combines the 16-day forecast with historical statistics and caches both datasets", async () => {
    const counter = { forecast: 0, archive: 0 };
    const service = new OpenMeteoWeatherService({
      forecastUrl: "https://forecast.test/v1/forecast",
      archiveUrl: "https://archive.test/v1/archive",
      fetcher: weatherFetcher(counter),
      now: () => new Date("2026-08-17T10:00:00.000Z"),
    });
    const window = { startDate: "2026-09-01", endDate: "2026-09-02" };

    const first = await service.forTrip(city, window);
    const second = await service.forTrip(city, window);

    assert.equal(first.available, true);
    assert.equal(first.source, "Open-Meteo Forecast + ERA5");
    assert.deepEqual(first.data.days, [
      {
        date: "2026-09-01",
        kind: "forecast",
        temperatureMinC: 14,
        temperatureMaxC: 21,
        precipitationProbabilityPct: 61,
        weatherCode: 63,
      },
      {
        date: "2026-09-02",
        kind: "climate",
        temperatureMinC: 12,
        temperatureMaxC: 22,
        precipitationFrequencyPct: 67,
        sampleSize: 3,
      },
    ]);
    assert.deepEqual(second.data, first.data);
    assert.deepEqual(counter, { forecast: 1, archive: 1 });
  });

  it("falls back to climate statistics when a short-range forecast request fails", async () => {
    let calls = 0;
    const fetcher = (async (input: Parameters<typeof fetch>[0]) => {
      calls += 1;
      const url = new URL(String(input));
      if (url.hostname === "forecast.test") {
        return new Response(JSON.stringify({ reason: "temporarily unavailable" }), {
          status: 503,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response(JSON.stringify({
        daily: {
          time: ["1991-08-30", "2005-09-01"],
          temperature_2m_min: [11, 13],
          temperature_2m_max: [19, 21],
          precipitation_sum: [0, 2],
        },
      }), { status: 200, headers: { "content-type": "application/json" } });
    }) as typeof fetch;
    const service = new OpenMeteoWeatherService({
      forecastUrl: "https://forecast.test/v1/forecast",
      archiveUrl: "https://archive.test/v1/archive",
      fetcher,
      now: () => new Date("2026-08-17T10:00:00.000Z"),
    });

    const result = await service.forTrip(city, { startDate: "2026-09-01", endDate: "2026-09-01" });

    assert.equal(result.available, true);
    assert.equal(result.data.days[0]?.kind, "climate");
    assert.match(result.warnings.join(" "), /прогноз погоды.+недоступен/iu);
    assert.equal(calls, 2);
  });

  it("returns an unavailable result instead of throwing when both APIs fail", async () => {
    const service = new OpenMeteoWeatherService({
      forecastUrl: "https://forecast.test/v1/forecast",
      archiveUrl: "https://archive.test/v1/archive",
      fetcher: (async () => new Response(JSON.stringify({ reason: "offline" }), {
        status: 503,
        headers: { "content-type": "application/json" },
      })) as typeof fetch,
      now: () => new Date("2026-08-17T10:00:00.000Z"),
    });

    const result = await service.forTrip(city, { startDate: "2026-09-01", endDate: "2026-09-02" });

    assert.equal(result.available, false);
    assert.deepEqual(result.data.days, []);
    assert.match(result.warnings.join(" "), /недоступ/iu);
  });
});
