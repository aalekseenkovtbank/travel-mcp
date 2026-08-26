import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { citySchema } from "@travel-growth-inspiration/contracts";

import { cities, findCity, findCityByName } from "../src/modules/catalog/cities.js";

describe("city catalog", () => {
  it("contains 20 valid cities with unique ids, names and IATA codes", () => {
    assert.equal(cities.length, 20);
    assert.deepEqual(
      cities.map((city) => citySchema.parse(city)),
      cities,
    );

    for (const field of ["id", "name", "iata"] as const) {
      const values = cities.map((city) => city[field].toLocaleLowerCase("ru"));
      assert.equal(new Set(values).size, cities.length, `${field} values must be unique`);
    }
  });

  it("provides at least 10 unique normalized tags for every city", () => {
    for (const city of cities) {
      assert.ok(city.tags.length >= 10, `${city.name} must have at least 10 tags`);
      assert.ok(
        city.tags.every((tag) => tag === tag.trim() && tag === tag.toLocaleLowerCase("ru")),
        `${city.name} tags must be trimmed and lowercase`,
      );
      assert.equal(
        new Set(city.tags).size,
        city.tags.length,
        `${city.name} tags must be unique`,
      );
    }
  });

  it("finds a newly added city by id and case-insensitive name", () => {
    assert.equal(findCity("krasnoyarsk")?.iata, "KJA");
    assert.equal(findCityByName("  КРАСНОЯРСК  ")?.id, "krasnoyarsk");
  });
});
