import type { City, DataMode, PreferenceProfile, TripBrief } from "@travel-growth-inspiration/contracts";

import type {
  DateWindow,
  EventInventoryItem,
  FlightInventoryItem,
  HotelInventoryItem,
  NearbyAnchor,
  NearbyPlace,
  NearbySearchOptions,
  PlannerDataProvider,
  ProviderResult,
} from "./provider-types.js";

type Mode = "auto" | "live" | "demo";

/**
 * Selects the provider without ever mixing real and demonstration inventory.
 *
 * `auto` is tolerant at the planner level (optional sources may be absent), while
 * `live` surfaces required-source errors. Both use the same real provider; demo
 * data is reachable only through the explicit `demo` mode.
 */
export class ResilientPlannerProvider implements PlannerDataProvider {
  readonly #live: PlannerDataProvider;
  readonly #demo: PlannerDataProvider;
  readonly #mode: Mode;

  constructor(live: PlannerDataProvider, demo: PlannerDataProvider, mode: Mode) {
    this.#live = live;
    this.#demo = demo;
    this.#mode = mode;
  }

  get dataMode(): DataMode {
    return this.#mode === "demo" ? "demo" : "real";
  }

  #selected(): PlannerDataProvider {
    return this.#mode === "demo" ? this.#demo : this.#live;
  }

  profile(): Promise<ProviderResult<PreferenceProfile>> {
    return this.#selected().profile();
  }

  flights(
    from: City,
    to: City,
    date: string,
    travelers: TripBrief["travelers"],
  ): Promise<ProviderResult<FlightInventoryItem[]>> {
    return this.#selected().flights(from, to, date, travelers);
  }

  hotels(
    city: City,
    window: DateWindow,
    travelers: TripBrief["travelers"],
  ): Promise<ProviderResult<HotelInventoryItem[]>> {
    return this.#selected().hotels(city, window, travelers);
  }

  events(
    city: City,
    window: DateWindow,
    interests: string[],
  ): Promise<ProviderResult<EventInventoryItem[]>> {
    return this.#selected().events(city, window, interests);
  }

  nearby(
    city: City,
    anchor: NearbyAnchor,
    options?: NearbySearchOptions,
  ): Promise<ProviderResult<NearbyPlace[]>> {
    return this.#selected().nearby(city, anchor, options);
  }

  async close(): Promise<void> {
    await Promise.allSettled([this.#live.close(), this.#demo.close()]);
  }
}
