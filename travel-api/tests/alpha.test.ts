import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type {
  City,
  PreferenceProfile,
  TripBrief,
  TripProposal,
} from "@travel-growth-inspiration/contracts";

import { OpenAiEditorialService, type EditorialService } from "../src/modules/editorial/editorial-service.js";
import { findCity } from "../src/modules/catalog/cities.js";
import { DemoPlannerProvider } from "../src/modules/providers/demo-planner-provider.js";
import { incomeCohort } from "../src/modules/providers/customer-profile.js";
import { OsmNearbyClient } from "../src/modules/providers/osm-nearby-client.js";
import type {
  DateWindow,
  EventInventoryItem,
  FlightInventoryItem,
  HotelInventoryItem,
  NearbyAnchor,
  NearbyPlace,
  PlannerDataProvider,
  ProviderResult,
} from "../src/modules/providers/provider-types.js";
import { ResilientPlannerProvider } from "../src/modules/providers/resilient-planner-provider.js";
import { TbankMcpClient, type McpJsonResult } from "../src/modules/providers/tbank-mcp-client.js";
import { TbankPlannerProvider } from "../src/modules/providers/tbank-planner-provider.js";
import {
  PreferredNearbyClient,
  TwoGisNearbyClient,
} from "../src/modules/providers/two-gis-nearby-client.js";
import { buildBehavioralInsights } from "../src/modules/providers/behavioral-profile.js";
import { TravelPlannerAgent } from "../src/modules/planner/travel-planner-agent.js";
import {
  hotelNightlyPriceRange,
  selectTripEvents,
  targetEventCount,
  TripCompiler,
} from "../src/modules/planner/trip-compiler.js";
import { TravelStore } from "../src/modules/storage/travel-store.js";

const brief: TripBrief = {
  preset: "weekend",
  originCityId: "saint-petersburg",
  destinationCityId: "moscow",
  travelers: { adults: 1, childrenAges: [] },
  time: { mode: "exact", startDate: "2026-09-18", endDate: "2026-09-21" },
  interests: ["концерты"],
};

const profile: PreferenceProfile = {
  generatedAt: "2026-08-16T10:00:00.000Z",
  source: "bank",
  analysisWindowDays: 90,
  transactionCount: 120,
  estimatedMonthlyIncomeRub: 150_000,
  incomeCohort: "100k_to_200k",
  incomeConfidence: "medium",
  monthlySpendRub: 100_000,
  diningSpendRub: 10_000,
  weekendAverageDailySpendRub: 4_500,
  weekdayAverageDailySpendRub: 3_000,
  weekendSpendSharePct: 35,
  averageCheckRub: 1_500,
  medianCheckRub: 900,
  categoryBreakdown: [{
    name: "Рестораны",
    monthlySpendRub: 10_000,
    sharePct: 10,
    averageCheckRub: 2_000,
    transactionCount: 5,
  }],
  diningProfile: {
    averageCheckRub: 2_000,
    medianCheckRub: 1_800,
    preferredCuisines: ["японская"],
    preferredVenueTypes: ["кафе и кофейни"],
  },
  shoppingProfile: {
    averageCheckRub: 1_200,
    medianCheckRub: 900,
    preferredStoreTypes: ["продукты и супермаркеты"],
  },
  preferredCategories: ["Рестораны"],
  favoriteMerchants: [],
  favoriteDiningMerchants: [],
  eventInterests: ["концерты"],
  previousDestinations: [],
  llmSummary: "Доходная когорта: 100–200 тыс. ₽/мес. Выходной день: 4 500 ₽.",
  notes: [],
};

const editorial: EditorialService = {
  decorate: async (proposals) => ({ proposals }),
  interpretChange: async (text) => ({
    action: text.includes("ресторан") ? "more_restaurants" : "general",
    instructions: text,
  }),
};

function result<T>(data: T, source: string): ProviderResult<T> {
  return {
    data,
    warnings: [],
    isFallback: false,
    source,
    checkedAt: "2026-08-16T10:00:00.000Z",
  };
}

function mcpResult<T>(data: T, source: string): McpJsonResult<T> {
  return {
    data,
    warnings: [],
    source,
    checkedAt: "2026-08-16T10:00:00.000Z",
    meta: {},
  };
}

class FlexibleProvider implements PlannerDataProvider {
  readonly dataMode = "real" as const;
  readonly hotelWindows: DateWindow[] = [];

  async profile() {
    return result(profile, "T-Bank");
  }

  async flights(from: City, to: City, date: string): Promise<ProviderResult<FlightInventoryItem[]>> {
    return result(
      [{
        offerId: `${from.iata}-${to.iata}-${date}`,
        summary: `${from.iata} → ${to.iata}`,
        priceRub: date.endsWith("26") || date.endsWith("30") ? 1_000 : 8_000,
        source: "T-Bank Avia",
        live: true,
        checkedAt: "2026-08-16T10:00:00.000Z",
      }],
      "T-Bank Avia",
    );
  }

  async hotels(_city: City, window: DateWindow): Promise<ProviderResult<HotelInventoryItem[]>> {
    this.hotelWindows.push(window);
    const nights = Math.max(
      1,
      Math.round((Date.parse(window.endDate) - Date.parse(window.startDate)) / 86_400_000),
    );
    return result(
      [{
        hotelId: `hotel-${window.startDate}`,
        name: "Отель",
        stars: 4,
        priceRub: (window.startDate.endsWith("26") ? 2_000 : 12_000) * nights,
        latitude: 55.75,
        longitude: 37.61,
        image: { url: "https://cdn.tbank.ru/hotel.jpg", source: "T-Bank Hotels" },
        source: "T-Bank Hotels",
        live: true,
        checkedAt: "2026-08-16T10:00:00.000Z",
      }],
      "T-Bank Hotels",
    );
  }

  async events(
    _city: City,
    _window: DateWindow,
    _interests: string[],
  ): Promise<ProviderResult<EventInventoryItem[]>> {
    return result([], "T-Bank Afisha");
  }

  async nearby(
    _city: City,
    _anchor: Parameters<PlannerDataProvider["nearby"]>[1],
    _options?: Parameters<PlannerDataProvider["nearby"]>[2],
  ): Promise<ProviderResult<NearbyPlace[]>> {
    return result([], "OpenStreetMap");
  }

  async close() {}
}

class ParallelFixedCityProvider extends FlexibleProvider {
  flightCalls = 0;
  hotelCalls = 0;
  activeFlights = 0;
  activeHotels = 0;
  maxActiveFlights = 0;
  maxActiveHotels = 0;
  #releaseSlow!: () => void;
  readonly #slowGate = new Promise<void>((resolve) => {
    this.#releaseSlow = resolve;
  });

  releaseSlowWindows(): void {
    this.#releaseSlow();
  }

  override async flights(
    from: City,
    to: City,
    date: string,
  ): Promise<ProviderResult<FlightInventoryItem[]>> {
    this.flightCalls += 1;
    this.activeFlights += 1;
    this.maxActiveFlights = Math.max(this.maxActiveFlights, this.activeFlights);
    try {
      await Promise.resolve();
      if (date !== "2026-09-01" && date !== "2026-09-05") await this.#slowGate;
      return result([{
        offerId: `${from.iata}-${to.iata}-${date}`,
        summary: `${from.iata} → ${to.iata}`,
        priceRub: 7_000,
        source: "T-Bank Avia",
        live: true,
        checkedAt: "2026-08-16T10:00:00.000Z",
      }], "T-Bank Avia");
    } finally {
      this.activeFlights -= 1;
    }
  }

  override async hotels(
    _city: City,
    window: DateWindow,
  ): Promise<ProviderResult<HotelInventoryItem[]>> {
    this.hotelCalls += 1;
    this.activeHotels += 1;
    this.maxActiveHotels = Math.max(this.maxActiveHotels, this.activeHotels);
    try {
      await Promise.resolve();
      if (window.startDate !== "2026-09-01") await this.#slowGate;
      const nights = Math.max(
        1,
        Math.round((Date.parse(window.endDate) - Date.parse(window.startDate)) / 86_400_000),
      );
      return result([{
        hotelId: `parallel-${window.startDate}`,
        name: `Отель ${window.startDate}`,
        stars: 4,
        priceRub: 7_000 * nights,
        latitude: 55.75,
        longitude: 37.61,
        source: "T-Bank Hotels",
        live: true,
        checkedAt: "2026-08-16T10:00:00.000Z",
      }], "T-Bank Hotels");
    } finally {
      this.activeHotels -= 1;
    }
  }
}

class CountingDemoProvider extends DemoPlannerProvider {
  calls = { profile: 0, flights: 0, hotels: 0, events: 0, nearby: 0 };

  override async profile() {
    this.calls.profile += 1;
    return super.profile();
  }

  override async flights(...args: Parameters<DemoPlannerProvider["flights"]>) {
    this.calls.flights += 1;
    return super.flights(...args);
  }

  override async hotels(...args: Parameters<DemoPlannerProvider["hotels"]>) {
    this.calls.hotels += 1;
    return super.hotels(...args);
  }

  override async events(...args: Parameters<DemoPlannerProvider["events"]>) {
    this.calls.events += 1;
    return super.events(...args);
  }

  override async nearby(...args: Parameters<DemoPlannerProvider["nearby"]>) {
    this.calls.nearby += 1;
    return super.nearby(...args);
  }
}

class GatedEnrichmentProvider extends DemoPlannerProvider {
  eventCalls = 0;
  activeEventCalls = 0;
  maxActiveEventCalls = 0;
  #releaseEvents!: () => void;
  readonly #eventGate = new Promise<void>((resolve) => {
    this.#releaseEvents = resolve;
  });

  releaseEvents(): void {
    this.#releaseEvents();
  }

  override async profile(): Promise<ProviderResult<PreferenceProfile>> {
    return result(profile, "T-Bank");
  }

  override async events(...args: Parameters<DemoPlannerProvider["events"]>) {
    this.eventCalls += 1;
    this.activeEventCalls += 1;
    this.maxActiveEventCalls = Math.max(this.maxActiveEventCalls, this.activeEventCalls);
    await this.#eventGate;
    try {
      return await super.events(...args);
    } finally {
      this.activeEventCalls -= 1;
    }
  }
}

class EventfulProvider extends FlexibleProvider {
  readonly nearbyAnchors: NearbyAnchor[] = [];

  override async events(_city: City, window: DateWindow, _interests: string[]): Promise<ProviderResult<EventInventoryItem[]>> {
    const items = Array.from({ length: 10 }, (_, index): EventInventoryItem => ({
      eventId: `event-${index}`,
      name: `Концерт ${index + 1}`,
      kind: "концерт",
      genres: ["концерты"],
      rating: 8 - index / 10,
      dateTime: `${new Date(Date.parse(`${window.startDate}T12:00:00Z`) + index * 86_400_000).toISOString().slice(0, 10)}T19:00:00`,
      venue: `Площадка ${index + 1}`,
      address: `Театральная улица, ${index + 1}`,
      latitude: 55.75 + index / 1_000,
      longitude: 37.61 + index / 1_000,
      priceRub: 1_000,
      image: { url: `https://kassa.rambler.ru/event-${index}.jpg`, source: "T-Bank Afisha" },
      source: "T-Bank Afisha",
      checkedAt: "2026-08-16T10:00:00.000Z",
    }));
    return result(items, "T-Bank Afisha");
  }

  override async nearby(
    _city: City,
    anchor: Parameters<PlannerDataProvider["nearby"]>[1],
    _options?: Parameters<PlannerDataProvider["nearby"]>[2],
  ) {
    this.nearbyAnchors.push(anchor);
    const restaurants = Array.from({ length: 6 }, (_, index): NearbyPlace => ({
      osmId: `${anchor.type}-${anchor.id}-${index}`,
      type: "restaurant",
      name: index === 5 ? "Дальний ресторан" : `Ресторан ${index + 1}`,
      latitude: 55.75 + index / 10_000,
      longitude: 37.61 + index / 10_000,
      cuisine: index === 0 ? "regional" : "international",
      distanceMeters: 100 + index * 100,
      source: "OpenStreetMap",
      checkedAt: "2026-08-16T10:00:00.000Z",
    }));
    const points: NearbyPlace[] = _options?.includePointsOfInterest ? [{
      osmId: `poi-${anchor.id}`,
      type: "poi",
      name: "Главный музей",
      latitude: 55.752,
      longitude: 37.612,
      image: {
        url: "https://upload.wikimedia.org/museum.jpg",
        source: "Wikimedia Commons",
        sourceUrl: "https://commons.wikimedia.org/wiki/File:Museum.jpg",
      },
      distanceMeters: 250,
      source: "OpenStreetMap",
      checkedAt: "2026-08-16T10:00:00.000Z",
    }] : [];
    return result([...restaurants, ...points], "OpenStreetMap");
  }
}

class SameDayReplacementProvider extends EventfulProvider {
  override async events(...args: Parameters<EventfulProvider["events"]>) {
    const response = await super.events(...args);
    const target = response.data.find((event) => event.eventId === "event-1")!;
    return {
      ...response,
      data: [
        ...response.data.map((event) =>
          event.eventId === target.eventId
            ? { ...event, name: "Русалочка. Любовь двух миров" }
            : event,
        ),
        {
          ...target,
          eventId: "event-1-alternative",
          name: "Другое событие в этот день",
        },
      ],
    };
  }
}

async function waitForJob(store: TravelStore, jobId: string): Promise<void> {
  for (let attempt = 0; attempt < 200; attempt += 1) {
    const status = store.getJob(jobId)?.status;
    if (status === "completed") return;
    if (status === "failed" || status === "interrupted") throw new Error(`Job ended as ${status}`);
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  throw new Error("Job did not finish");
}

async function waitForCondition(condition: () => boolean): Promise<void> {
  for (let attempt = 0; attempt < 200; attempt += 1) {
    if (condition()) return;
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  throw new Error("Condition did not become true in time");
}

describe("Local alpha data behavior", () => {
  it("assigns stable income cohorts at every MVP boundary", () => {
    assert.deepEqual(
      [0, 50_000, 50_001, 100_000, 100_001, 200_000, 200_001, 500_000, 500_001, 1_000_000, 1_000_001]
        .map(incomeCohort),
      [
        "unknown",
        "up_to_50k",
        "50k_to_100k",
        "50k_to_100k",
        "100k_to_200k",
        "100k_to_200k",
        "200k_to_500k",
        "200k_to_500k",
        "500k_to_1m",
        "500k_to_1m",
        "1m_plus",
      ],
    );
  });

  it("raises the minimum hotel level together with the income cohort", () => {
    assert.equal(hotelNightlyPriceRange("up_to_50k").minRub, 1_800);
    assert.equal(hotelNightlyPriceRange("200k_to_500k").minRub, 7_000);
    assert.equal(hotelNightlyPriceRange("500k_to_1m").minRub, 12_000);
    assert.ok(
      hotelNightlyPriceRange("500k_to_1m").minRub >
        hotelNightlyPriceRange("100k_to_200k").maxRub / 2,
    );
  });

  it("calculates one event for every started three-day block", () => {
    assert.deepEqual(
      [2, 3, 4, 6, 7, 10].map((days) => targetEventCount("2026-09-01", `2026-09-${String(days).padStart(2, "0")}`)),
      [1, 1, 2, 2, 3, 4],
    );
  });

  it("builds a useful bank profile without retaining order ids or guest identity", () => {
    const insights = buildBehavioralInsights({
      operations: [{
        id: "SECRET_OPERATION_ID",
        occurredAt: "2026-08-08T20:15:00+03:00",
        type: "Debit",
        amount: -2_500,
        currency: "RUB",
        description: "Билеты на концерт",
        category: "Развлечения",
      }],
      orders: [{
        orderId: "SECRET_ORDER_ID",
        objectType: "concert",
        status: "DONE",
        amount: 6_000,
        createdAt: "2026-07-01T10:00:00+03:00",
        title: "Инди-фестиваль",
        eventName: "Инди-фестиваль",
        hotelName: "",
        destination: "Москва",
      }, {
        orderId: "SECRET_HOTEL_ORDER",
        objectType: "hotelBooking",
        status: "DONE",
        amount: 30_000,
        createdAt: "2026-06-01T10:00:00+03:00",
        title: "Отель",
        eventName: "",
        hotelName: "Отель",
        destination: "Казань",
      }],
      eventDetails: [{
        orderId: "SECRET_ORDER_ID",
        status: "DONE",
        createdAt: "2026-07-01T10:00:00+03:00",
        eventName: "Инди-фестиваль",
        genres: ["инди", "рок"],
        venue: "Клуб",
        address: "Секретный адрес",
        startDateTime: "2026-07-05T20:00:00+03:00",
        hallName: "Зал",
        seatCount: 2,
        ticketPricesRub: [3_000, 3_000],
        totalAmountRub: 6_000,
      }],
      travelDetails: [{
        orderId: "SECRET_HOTEL_ORDER",
        kind: "hotelBooking",
        status: "DONE",
        amountRub: 30_000,
        createdAt: "2026-06-01T10:00:00+03:00",
        title: "Отель",
        destination: "Казань",
        detailsAvailable: true,
        checkInDate: "2026-06-10",
        checkOutDate: "2026-06-13",
        hotelName: "Отель",
        hotelStars: 4,
        mealTypes: ["Завтрак"],
        roomCount: 1,
        guestCount: 2,
      }],
      audience: { ageBand: "25_34", adultContentAllowed: true },
      analysisWindowDays: 90,
    });

    assert.equal(insights.events.purchaseCount, 1);
    assert.deepEqual(insights.events.genreAffinities.map((item) => item.value), ["инди", "рок"]);
    assert.equal(insights.events.averagePartySize, 2);
    assert.equal(insights.leisureSpending.monthlySpendRub, 833);
    assert.deepEqual(insights.travel.preferredHotelStars.map((item) => item.value), ["4★"]);
    assert.equal(insights.travel.averageHotelNights, 3);
    assert.doesNotMatch(JSON.stringify(insights), /SECRET_|Секретный адрес/u);
  });

  it("uses purchase affinities and safe age restrictions when ranking events", () => {
    const insights = buildBehavioralInsights({
      operations: [],
      orders: [{
        orderId: "past",
        objectType: "concert",
        status: "DONE",
        amount: 4_000,
        createdAt: "2026-07-01",
        title: "Инди-концерт",
        eventName: "Инди-концерт",
        hotelName: "",
        destination: "Москва",
      }],
      eventDetails: [{
        orderId: "past",
        status: "DONE",
        createdAt: "2026-07-01",
        eventName: "Инди-концерт",
        genres: ["инди"],
        venue: "Любимый клуб",
        address: "",
        startDateTime: "2026-07-05T20:00:00+03:00",
        hallName: "",
        seatCount: 1,
        ticketPricesRub: [4_000],
        totalAmountRub: 4_000,
      }],
      travelDetails: [],
      audience: { ageBand: "16_17", adultContentAllowed: false },
      analysisWindowDays: 90,
    });
    const selected = selectTripEvents([
      {
        eventId: "generic",
        name: "Главный концерт",
        kind: "концерт",
        genres: ["поп"],
        rating: 10,
        dateTime: "2026-09-19T20:00:00+03:00",
        ageRestriction: "18+",
        priceRub: 4_000,
        source: "T-Bank",
        checkedAt: "2026-08-17T10:00:00.000Z",
      },
      {
        eventId: "preferred",
        name: "Инди-вечер",
        kind: "концерт",
        genres: ["инди"],
        rating: 7,
        dateTime: "2026-09-19T20:00:00+03:00",
        ageRestriction: "16+",
        priceRub: 4_000,
        source: "T-Bank",
        checkedAt: "2026-08-17T10:00:00.000Z",
      },
    ], brief, { ...profile, behavioralInsights: insights }, {
      startDate: "2026-09-18",
      endDate: "2026-09-20",
    });

    assert.deepEqual(selected.map((event) => event.eventId), ["preferred"]);
  });

  it("uses an LLM Proxy-compatible JSON result to understand an event replacement", async () => {
    const originalFetch = globalThis.fetch;
    let requestBody = "";
    globalThis.fetch = async (_input, init) => {
      requestBody = String(init?.body ?? "");
      const content = JSON.stringify({
        action: "replace_event",
        destinationName: null,
        eventName: "Русалочка. Любовь двух миров",
        eventDate: "2026-09-20",
        budgetRub: null,
        startDate: null,
        endDate: null,
        instructions: "Заменить Русалочку другим событием в тот же день",
      });
      return new Response(JSON.stringify({
        id: "chatcmpl_test",
        object: "chat.completion",
        created: 0,
        model: "deepseek-v4-flash-0731",
        choices: [{
          index: 0,
          message: { role: "assistant", content },
          finish_reason: "stop",
        }],
        usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
      }), { status: 200, headers: { "content-type": "application/json" } });
    };
    const service = new OpenAiEditorialService("test-key", "deepseek-v4-flash-0731", 1_000);
    const current = {
      destination: { name: "Москва" },
      startDate: "2026-09-18",
      endDate: "2026-09-24",
      totalPrice: { amount: 100_000 },
      hotel: { name: "Отель" },
      events: [
        { name: "Концерт 2", dateTime: "2026-09-19T19:00:00" },
        { name: "Русалочка. Любовь двух миров", dateTime: "2026-09-20T14:30:00" },
      ],
    } as unknown as TripProposal;
    try {
      assert.deepEqual(
        await service.interpretChange(
          "Не хочу на русалочку, добавь что-то другое в этот день",
          current,
        ),
        {
          action: "replace_event",
          eventName: "Русалочка. Любовь двух миров",
          eventDate: "2026-09-20",
          instructions: "Заменить Русалочку другим событием в тот же день",
        },
      );
      assert.ok(requestBody.includes("Не хочу на русалочку"));
      assert.ok(requestBody.includes("Русалочка. Любовь двух миров"));
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("uses an independent LLM review to correct a misclassified date move", async () => {
    const originalFetch = globalThis.fetch;
    let calls = 0;
    let reviewedRequest = "";
    globalThis.fetch = async (_input, init) => {
      calls += 1;
      reviewedRequest = String(init?.body ?? "");
      const content = JSON.stringify(calls === 1
        ? {
            action: "replace_event",
            destinationName: null,
            eventName: null,
            eventDate: null,
            budgetRub: null,
            startDate: null,
            endDate: null,
            flightDirection: null,
            flightPreference: null,
            hotelPreference: null,
            instructions: "Заменить события",
          }
        : {
            action: "change_dates",
            destinationName: null,
            eventName: null,
            eventDate: null,
            budgetRub: null,
            startDate: "2026-09-01",
            endDate: "2026-09-04",
            flightDirection: null,
            flightPreference: null,
            hotelPreference: null,
            instructions: "Перенести поездку на начало сентября, сохранив 3 ночи",
          });
      return new Response(JSON.stringify({
        id: `chatcmpl_date_change_${calls}`,
        object: "chat.completion",
        created: 0,
        model: "gpt-5.6-terra",
        choices: [{ index: 0, message: { role: "assistant", content }, finish_reason: "stop" }],
        usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
      }), { status: 200, headers: { "content-type": "application/json" } });
    };
    const service = new OpenAiEditorialService("test-key", "gpt-5.6-terra");
    const current = {
      destination: { name: "Казань" },
      startDate: "2026-08-21",
      endDate: "2026-08-24",
      totalPrice: { amount: 68_649 },
      hotel: { name: "Korston Роял 5*" },
      events: [],
    } as unknown as TripProposal;
    try {
      assert.deepEqual(
        await service.interpretChange("Хочу не 21 августа, а в начале сеньтября", current),
        {
          action: "change_dates",
          startDate: "2026-09-01",
          endDate: "2026-09-04",
          instructions: "Перенести поездку на начало сентября, сохранив 3 ночи",
        },
      );
      assert.equal(calls, 2);
      assert.match(reviewedRequest, /firstInterpretation/u);
      assert.match(reviewedRequest, /replace_event/u);
      assert.match(reviewedRequest, /durationNights/u);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("asks the LLM to repair duplicate route titles before accepting decorations", async () => {
    const originalFetch = globalThis.fetch;
    let calls = 0;
    let repairRequest = "";
    globalThis.fetch = async (_input, init) => {
      calls += 1;
      repairRequest = String(init?.body ?? "");
      const decorations = calls === 1
        ? [
            { proposalId: "proposal-1", title: "Выходные в Казани", tagline: "Первый вариант", fitReasons: ["Подходит по бюджету"] },
            { proposalId: "proposal-2", title: "Выходные в Казани", tagline: "Второй вариант", fitReasons: ["Больше комфорта"] },
          ]
        : [
            { proposalId: "proposal-1", title: "Казань без переплаты", tagline: "Практичный городской маршрут", fitReasons: ["Подходит по бюджету"] },
            { proposalId: "proposal-2", title: "Казань с видом на Кремль", tagline: "Больше комфорта в центре", fitReasons: ["Больше комфорта"] },
          ];
      const content = JSON.stringify({ decorations });
      return new Response(JSON.stringify({
        id: `chatcmpl_decorations_${calls}`,
        object: "chat.completion",
        created: 0,
        model: "gpt-5.6-terra",
        choices: [{ index: 0, message: { role: "assistant", content }, finish_reason: "stop" }],
        usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
      }), { status: 200, headers: { "content-type": "application/json" } });
    };
    const proposals = [
      {
        id: "proposal-1",
        destination: { name: "Казань", tags: [] },
        totalPrice: { amount: 45_000 },
        tier: "cohort_floor",
        hotel: { name: "Давыдов" },
        events: [],
        restaurantGroups: [],
      },
      {
        id: "proposal-2",
        destination: { name: "Казань", tags: [] },
        totalPrice: { amount: 72_000 },
        tier: "cohort_ceiling",
        hotel: { name: "Kazan Palace" },
        events: [],
        restaurantGroups: [],
      },
    ] as unknown as TripProposal[];
    try {
      const service = new OpenAiEditorialService("test-key", "gpt-5.6-terra");
      const result = await service.decorate(proposals, profile, brief);

      assert.equal(calls, 2);
      assert.deepEqual(result.proposals.map((proposal) => proposal.title), [
        "Казань без переплаты",
        "Казань с видом на Кремль",
      ]);
      assert.match(repairRequest, /Title duplicates/u);
      assert.match(repairRequest, /rejectedDecorations/u);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("uses the LLM to turn an earlier arrival request into a directed flight preference", async () => {
    const originalFetch = globalThis.fetch;
    let requestBody = "";
    globalThis.fetch = async (_input, init) => {
      requestBody = String(init?.body ?? "");
      const content = JSON.stringify({
        action: "replace_flight",
        destinationName: null,
        eventName: null,
        eventDate: null,
        budgetRub: null,
        startDate: null,
        endDate: null,
        flightDirection: "outbound",
        flightPreference: "earlier_arrival",
        instructions: "Прилететь в Москву раньше",
      });
      return new Response(JSON.stringify({
        id: "chatcmpl_flight_change",
        object: "chat.completion",
        created: 0,
        model: "deepseek-v4-flash-0731",
        choices: [{
          index: 0,
          message: { role: "assistant", content },
          finish_reason: "stop",
        }],
        usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
      }), { status: 200, headers: { "content-type": "application/json" } });
    };
    const service = new OpenAiEditorialService("test-key", "deepseek-v4-flash-0731", 1_000);
    const current = {
      destination: { name: "Москва" },
      startDate: "2026-09-03",
      endDate: "2026-09-06",
      totalPrice: { amount: 62_480 },
      hotel: { name: "Москва Марриотт Империал Плаза" },
      flights: {
        outbound: {
          summary: "Победа LED→SVO 21:25",
          departureTime: "21:25",
          arrivalTime: "22:55",
        },
        return: {
          summary: "Победа SVO→LED 10:25",
          departureTime: "10:25",
          arrivalTime: "11:55",
        },
      },
      events: [],
    } as unknown as TripProposal;
    try {
      assert.deepEqual(
        await service.interpretChange("Хочу пораньше прилететь в москву", current),
        {
          action: "replace_flight",
          flightDirection: "outbound",
          flightPreference: "earlier_arrival",
          instructions: "Прилететь в Москву раньше",
        },
      );
      assert.ok(requestBody.includes("Победа LED→SVO 21:25"));
      assert.ok(requestBody.includes("22:55"));
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("persists clickable core trips before optional enrichment and enriches three in parallel", async () => {
    const store = new TravelStore(":memory:");
    const provider = new GatedEnrichmentProvider();
    const agent = new TravelPlannerAgent(store, provider, editorial);
    const accepted = agent.createRun({ ...brief, destinationCityId: undefined });
    try {
      await waitForCondition(() =>
        store.getEvents(accepted.jobId).filter((event) => event.type === "trip.partial").length === 3 &&
        provider.activeEventCalls === 3,
      );
      const events = store.getEvents(accepted.jobId);
      const partials = events.filter((event) => event.type === "trip.partial");
      assert.equal(provider.eventCalls, 3);
      assert.equal(provider.maxActiveEventCalls, 3);
      assert.equal(store.getJob(accepted.jobId)?.status, "running");
      assert.equal(store.getRun(accepted.runId!)?.trips.length, 3);
      assert.ok(partials.every((event) => event.data.stage === "core"));
      assert.ok(partials.every((event) => {
        const proposal = event.data.proposal as TripProposal;
        const dailySpend = proposal.priceBreakdown.find((item) => item.label === "Траты на месте");
        return dailySpend?.price.amount === 18_000 &&
          dailySpend.price.source === "Средние траты клиента в выходной";
      }));
      assert.ok(partials.every((event) => {
        const proposal = event.data.proposal as TripProposal;
        const trip = store.getTrip(proposal.id);
        return trip?.preparationStatus === "preparing" &&
          trip.revisionCount === 1 &&
          !trip.latestRevision.proposal.sources.some((source) => source.component === "editorial");
      }));

      provider.releaseEvents();
      await waitForJob(store, accepted.jobId);
      const finishedEvents = store.getEvents(accepted.jobId);
      const ready = finishedEvents.filter((event) => event.type === "trip.ready");
      assert.equal(ready.length, 3);
      assert.ok(ready.every((event) => event.data.stage === "enriched"));
      assert.ok(ready.every((event) => {
        const proposal = event.data.proposal as TripProposal;
        const trip = store.getTrip(proposal.id);
        return trip?.preparationStatus === "ready" &&
          trip.revisionCount === 1 &&
          trip.latestRevision.proposal.sources.some((source) => source.component === "editorial");
      }));
      assert.equal(finishedEvents.at(-1)?.type, "job.completed");
    } finally {
      provider.releaseEvents();
      store.close();
    }
  });

  it("keeps restaurants out of the timeline and groups up to three around every anchor", async () => {
    const provider = new EventfulProvider();
    const compiler = new TripCompiler(provider, editorial);
    const compiled = await compiler.compile("run-events", {
      ...brief,
      time: { mode: "exact", startDate: "2026-09-18", endDate: "2026-09-24" },
    }, profile);
    const proposal = compiled.proposals[0]!;
    assert.equal(proposal.events.length, 3);
    assert.equal(new Set(proposal.events.map((event) => event.dateTime?.slice(0, 10))).size, 3);
    assert.equal(proposal.restaurantGroups.length, 4);
    assert.ok(proposal.restaurantGroups.every((group) => group.restaurants.length === 3));
    assert.ok(proposal.itinerary.every((item) => !/^Обед:/u.test(item.title)));
    assert.equal(proposal.hotel.image?.url, "https://cdn.tbank.ru/hotel.jpg");
    assert.equal(proposal.hotel.mapPoint.image?.url, proposal.hotel.image?.url);
    assert.ok(proposal.events.every((event) => event.image && event.mapPoint?.image));
    assert.equal(
      proposal.mapPoints.find((point) => point.type === "poi")?.image?.source,
      "Wikimedia Commons",
    );
    const store = new TravelStore(":memory:");
    try {
      const runId = store.createRun(brief, "real");
      store.createTrip(runId, proposal, brief);
      assert.equal(
        store.getTrip(proposal.id)?.latestRevision.proposal.events[0]?.image?.source,
        "T-Bank Afisha",
      );
    } finally {
      store.close();
    }
    assert.deepEqual(
      provider.nearbyAnchors
        .filter((anchor) => anchor.type === "event")
        .map((anchor) => anchor.address),
      ["Театральная улица, 1", "Театральная улица, 2", "Театральная улица, 3"],
    );
  });

  it("preserves an event venue address returned by the Afisha schedule", async () => {
    const fakeMcp = {
      async callJson<T>(name: string, args: Record<string, unknown>): Promise<McpJsonResult<T>> {
        if (name === "afisha_catalog") {
          return mcpResult({
            kind: args.kind,
            city: "Москва",
            dateFrom: "2026-09-18",
            dateTo: "2026-09-21",
            scanned: 1,
            total: 1,
            events: [{
              eventId: `event-${args.kind}`,
              name: `Событие ${args.kind}`,
              kind: args.kind,
              genres: [],
              ageRestriction: "0+",
              rating: 8,
              imageUrl: "https://kassa.rambler.ru/poster.jpg",
              slots: [{
                startDateTime: "2026-09-19T19:00:00+03:00",
                slotId: `slot-${args.kind}`,
                priceFix: 1_500,
                priceMin: null,
                priceMax: null,
              }],
            }],
          }, "T-Bank Afisha") as unknown as McpJsonResult<T>;
        }
        if (name === "concert_schedule") {
          return mcpResult({
            eventId: args.event_id,
            kind: args.kind,
            showings: [{
              eventId: args.event_id,
              objectId: "venue-1",
              venue: "Театр Эстрады",
              address: "Берсеневская набережная, 20/2",
              latitude: null,
              longitude: null,
              startDateTime: "2026-09-19T19:00:00+03:00",
              slotId: `slot-${args.kind}`,
              priceFix: 1_500,
              priceMin: null,
              priceMax: null,
            }],
          }, "T-Bank Afisha") as unknown as McpJsonResult<T>;
        }
        throw new Error(`Unexpected tool: ${name}`);
      },
      close: async () => undefined,
    };
    const provider = new TbankPlannerProvider(
      fakeMcp as unknown as TbankMcpClient,
      new OsmNearbyClient("https://overpass.example.test", "https://nominatim.example.test", 1_000),
    );
    const events = await provider.events(
      findCity("moscow")!,
      { startDate: "2026-09-18", endDate: "2026-09-21" },
      ["концерты"],
    );
    assert.ok(events.data.length > 0);
    const scheduled = events.data.filter((event) => event.kind !== "кино");
    assert.ok(scheduled.every((event) => event.venue === "Театр Эстрады"));
    assert.ok(scheduled.every((event) => event.address === "Берсеневская набережная, 20/2"));
    assert.ok(events.data.every((event) => event.image?.url === "https://kassa.rambler.ru/poster.jpg"));
    assert.ok(events.data.every((event) => event.ageRestriction === "0+"));
  });

  it("distributes Afisha schedule lookups across trip days", async () => {
    const scheduleCalls: string[] = [];
    const fakeMcp = {
      async callJson<T>(name: string, args: Record<string, unknown>): Promise<McpJsonResult<T>> {
        if (name === "afisha_catalog") {
          const kind = String(args.kind);
          const events = kind === "концерт"
            ? Array.from({ length: 6 }, (_, index) => ({
                eventId: `event-${index}`,
                name: `Концерт ${index}`,
                kind,
                genres: ["концерты"],
                ageRestriction: "0+",
                rating: 10 - index,
                slots: [{
                  startDateTime: `${index < 4 ? "2026-09-18" : index === 4 ? "2026-09-19" : "2026-09-20"}T19:00:00+03:00`,
                  slotId: `slot-${index}`,
                  priceFix: 1_500,
                  priceMin: null,
                  priceMax: null,
                }],
              }))
            : [];
          return mcpResult({
            kind,
            city: "Москва",
            dateFrom: "2026-09-18",
            dateTo: "2026-09-21",
            scanned: events.length,
            total: events.length,
            events,
          }, "T-Bank Afisha") as unknown as McpJsonResult<T>;
        }
        if (name === "concert_schedule") {
          const eventId = String(args.event_id);
          const index = Number(eventId.split("-").at(-1));
          const date = index < 4 ? "2026-09-18" : index === 4 ? "2026-09-19" : "2026-09-20";
          scheduleCalls.push(eventId);
          return mcpResult({
            eventId,
            kind: String(args.kind),
            showings: [{
              eventId,
              objectId: `venue-${index}`,
              venue: `Площадка ${index}`,
              address: `Улица, ${index}`,
              latitude: 55.75 + index / 1_000,
              longitude: 37.61 + index / 1_000,
              startDateTime: `${date}T19:00:00+03:00`,
              slotId: `slot-${index}`,
              priceFix: 1_500,
              priceMin: null,
              priceMax: null,
            }],
          }, "T-Bank Afisha") as unknown as McpJsonResult<T>;
        }
        throw new Error(`Unexpected tool: ${name}`);
      },
      close: async () => undefined,
    };
    const provider = new TbankPlannerProvider(
      fakeMcp as unknown as TbankMcpClient,
      new OsmNearbyClient("https://overpass.example.test", "https://nominatim.example.test", 1_000),
    );

    const events = await provider.events(
      findCity("moscow")!,
      { startDate: "2026-09-18", endDate: "2026-09-21" },
      ["концерты"],
    );

    assert.equal(scheduleCalls.length, 4);
    assert.ok(scheduleCalls.includes("event-0"));
    assert.ok(scheduleCalls.includes("event-4"));
    assert.ok(scheduleCalls.includes("event-5"));
    assert.equal(events.data.find((event) => event.eventId === "event-4")?.venue, "Площадка 4");
    assert.equal(events.data.find((event) => event.eventId === "event-5")?.address, "Улица, 5");
  });

  it("does not duplicate a venue name in the geocoding query", async () => {
    const originalFetch = globalThis.fetch;
    let geocodingQuery = "";
    globalThis.fetch = async (input) => {
      const url = String(input);
      if (url.startsWith("https://nominatim.example.test")) {
        geocodingQuery = new URL(url).searchParams.get("q") ?? "";
        return new Response(JSON.stringify([{ lat: "55.8298", lon: "37.6330" }]), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      if (url === "https://overpass.example.test") {
        return new Response(JSON.stringify({
          elements: [{
            id: 1,
            type: "node",
            lat: 55.83,
            lon: 37.634,
            tags: { amenity: "restaurant", name: "Ресторан у площадки" },
          }],
        }), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      throw new Error(`Unexpected URL: ${url}`);
    };
    try {
      const client = new OsmNearbyClient(
        "https://overpass.example.test",
        "https://nominatim.example.test",
        1_000,
      );
      const nearby = await client.nearby(findCity("moscow")!, {
        id: "event-1",
        type: "event",
        name: "Москвариум",
        address: "Москвариум",
      });
      assert.equal(geocodingQuery, "Москвариум, Москва, Россия");
      assert.equal(nearby.data[0]?.name, "Ресторан у площадки");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("maps rich 2GIS restaurant fields into the nearby contract", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (input) => {
      const url = new URL(String(input));
      assert.equal(url.origin + url.pathname, "https://catalog.example.test/3.0/items");
      assert.equal(url.searchParams.get("key"), "test-key");
      assert.equal(url.searchParams.get("point"), "37.61,55.75");
      assert.equal(url.searchParams.get("radius"), "1800");
      assert.equal(url.searchParams.get("page_size"), "10");
      assert.match(url.searchParams.get("fields") ?? "", /items\.reviews/u);
      return new Response(JSON.stringify({
        meta: { code: 200 },
        result: {
          items: [{
            id: "70000001012345678_suffix",
            name: "Татарская усадьба",
            type: "branch",
            full_address_name: "Москва, Тверская улица, 1",
            city_alias: "moscow",
            point: { lat: 55.751, lon: 37.611 },
            reviews: { general_rating: 4.7, general_review_count: 238 },
            schedule: { is_24x7: true },
            attribute_groups: [{
              attributes: [
                { name: "Татарская кухня", tag: "food_service_cuisine" },
                { name: "Средний чек 1500 ₽", tag: "food_service_avg_price" },
                { name: "Wi-Fi", tag: "wifi" },
                { name: "Доставка", tag: "delivery" },
              ],
            }],
          }],
        },
      }), { status: 200, headers: { "content-type": "application/json" } });
    };
    try {
      const client = new TwoGisNearbyClient(
        "https://catalog.example.test/3.0/items",
        "test-key",
        1_000,
      );
      const nearby = await client.nearby(findCity("moscow")!, {
        id: "hotel-1",
        type: "hotel",
        name: "Отель",
        latitude: 55.75,
        longitude: 37.61,
      });
      assert.equal(nearby.source, "2ГИС");
      assert.equal(nearby.data.length, 1);
      assert.deepEqual(nearby.data[0], {
        osmId: "2gis/70000001012345678",
        type: "restaurant",
        name: "Татарская усадьба",
        latitude: 55.751,
        longitude: 37.611,
        cuisine: "Татарская кухня",
        openingHours: "Круглосуточно",
        address: "Москва, Тверская улица, 1",
        rating: 4.7,
        reviewCount: 238,
        averageCheck: "Средний чек 1500 ₽",
        attributes: ["Wi-Fi", "Доставка"],
        delivery: true,
        sourceUrl: "https://2gis.ru/moscow/firm/70000001012345678",
        distanceMeters: 128,
        source: "2ГИС",
        checkedAt: nearby.checkedAt,
      });
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("combines 2GIS restaurants with OSM points and falls back to OSM", async () => {
    const originalFetch = globalThis.fetch;
    let twoGisAvailable = true;
    globalThis.fetch = async (input) => {
      const url = String(input);
      if (url.startsWith("https://catalog.example.test")) {
        if (!twoGisAvailable) return new Response("unavailable", { status: 503 });
        return new Response(JSON.stringify({
          meta: { code: 200 },
          result: { items: [{
            id: "7000000101",
            name: "Ресторан 2ГИС",
            point: { lat: 55.751, lon: 37.611 },
          }] },
        }), { status: 200, headers: { "content-type": "application/json" } });
      }
      if (url === "https://overpass.example.test") {
        return new Response(JSON.stringify({
          elements: [
            { id: 1, type: "node", lat: 55.751, lon: 37.611, tags: { amenity: "restaurant", name: "Ресторан OSM" } },
            { id: 2, type: "node", lat: 55.752, lon: 37.612, tags: { tourism: "museum", name: "Музей OSM" } },
          ],
        }), { status: 200, headers: { "content-type": "application/json" } });
      }
      throw new Error(`Unexpected URL: ${url}`);
    };
    try {
      const osm = new OsmNearbyClient(
        "https://overpass.example.test",
        "https://nominatim.example.test",
        1_000,
      );
      const client = new PreferredNearbyClient(
        osm,
        new TwoGisNearbyClient("https://catalog.example.test/3.0/items", "test-key", 1_000),
      );
      const anchor: NearbyAnchor = {
        id: "hotel-1",
        type: "hotel",
        name: "Отель",
        latitude: 55.75,
        longitude: 37.61,
      };
      const combined = await client.nearby(findCity("moscow")!, anchor, {
        includePointsOfInterest: true,
      });
      assert.equal(combined.source, "2ГИС + OpenStreetMap");
      assert.deepEqual(combined.data.map((place) => place.name), ["Ресторан 2ГИС", "Музей OSM"]);

      twoGisAvailable = false;
      const fallback = await client.nearby(findCity("moscow")!, anchor);
      assert.equal(fallback.source, "OpenStreetMap");
      assert.equal(fallback.isFallback, true);
      assert.equal(fallback.data[0]?.name, "Ресторан OSM");
      assert.ok(fallback.warnings.some((warning) => warning.includes("2ГИС временно недоступен")));
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("normalizes a full event address before geocoding nearby restaurants", async () => {
    const originalFetch = globalThis.fetch;
    const geocodingQueries: string[] = [];
    globalThis.fetch = async (input) => {
      const url = String(input);
      if (url.startsWith("https://nominatim.example.test")) {
        geocodingQueries.push(new URL(url).searchParams.get("q") ?? "");
        return new Response(JSON.stringify([{ lat: "56.3165", lon: "44.0105" }]), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      if (url === "https://overpass.example.test") {
        return new Response(JSON.stringify({
          elements: [{
            id: 10,
            type: "node",
            lat: 56.317,
            lon: 44.011,
            tags: { amenity: "restaurant", name: "Ресторан у ТЮЗа" },
          }],
        }), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      throw new Error(`Unexpected URL: ${url}`);
    };
    try {
      const client = new OsmNearbyClient(
        "https://overpass.example.test",
        "https://nominatim.example.test",
        1_000,
      );
      const nearby = await client.nearby(findCity("nizhny-novgorod")!, {
        id: "event-2",
        type: "event",
        name: "Театр юного зрителя, ТЮЗ",
        address: "г. Нижний Новгород, улица Максима Горького, дом 145",
      });
      assert.deepEqual(geocodingQueries, [
        "улица Максима Горького, 145, Нижний Новгород, Россия",
      ]);
      assert.equal(nearby.data[0]?.name, "Ресторан у ТЮЗа");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("falls back to bounded OpenStreetMap search when Overpass is unavailable", async () => {
    const originalFetch = globalThis.fetch;
    let overpassCalls = 0;
    globalThis.fetch = async (input) => {
      const url = String(input);
      if (url === "https://overpass.example.test") {
        overpassCalls += 1;
        return new Response("unavailable", { status: 503 });
      }
      if (url.startsWith("https://nominatim.example.test")) {
        const requestUrl = new URL(url);
        assert.equal(requestUrl.searchParams.get("bounded"), "1");
        return new Response(JSON.stringify(Array.from({ length: 4 }, (_, index) => ({
          osm_type: "node",
          osm_id: 100 + index,
          lat: String(56.3166 + index / 10_000),
          lon: String(44.0106 + index / 10_000),
          category: "amenity",
          type: "restaurant",
          name: `Резервный ресторан ${index + 1}`,
          display_name: `Резервный ресторан ${index + 1}, Нижний Новгород`,
        }))), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      throw new Error(`Unexpected URL: ${url}`);
    };
    try {
      const client = new OsmNearbyClient(
        "https://overpass.example.test",
        "https://nominatim.example.test",
        1_000,
      );
      const nearby = await client.nearby(findCity("nizhny-novgorod")!, {
        id: "event-3",
        type: "event",
        name: "ТЮЗ",
        latitude: 56.3165,
        longitude: 44.0105,
      });
      assert.equal(overpassCalls, 2);
      assert.equal(nearby.data.length, 3);
      assert.equal(nearby.isFallback, true);
      assert.ok(nearby.data.every((place) => place.type === "restaurant"));
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("enriches only exact Wikimedia-tagged points and keeps failures optional", async () => {
    const originalFetch = globalThis.fetch;
    let commonsCalls = 0;
    let wikipediaCalls = 0;
    globalThis.fetch = async (input) => {
      const url = String(input);
      if (url === "https://overpass.example.test") {
        return new Response(JSON.stringify({
          elements: [
            { id: 1, type: "node", lat: 55.751, lon: 37.611, tags: { tourism: "museum", name: "Commons музей", wikimedia_commons: "File:Commons Museum.jpg" } },
            { id: 2, type: "node", lat: 55.752, lon: 37.612, tags: { historic: "yes", name: "Wikipedia место", wikipedia: "ru:Историческое место" } },
            { id: 3, type: "node", lat: 55.753, lon: 37.613, tags: { tourism: "attraction", name: "Непроверенная картинка", image: "https://untrusted.example.test/place.jpg" } },
            { id: 4, type: "node", lat: 55.754, lon: 37.614, tags: { tourism: "gallery", name: "Нет файла", wikimedia_commons: "File:Missing.jpg" } },
            { id: 5, type: "node", lat: 55.755, lon: 37.615, tags: { tourism: "viewpoint", name: "Таймаут", wikimedia_commons: "File:Timeout.jpg" } },
            { id: 6, type: "node", lat: 55.756, lon: 37.616, tags: { tourism: "museum", name: "Без тега изображения" } },
          ],
        }), { status: 200, headers: { "content-type": "application/json" } });
      }
      if (url.includes("File%3ACommons%20Museum.jpg")) {
        commonsCalls += 1;
        return new Response(JSON.stringify({
          file_description_url: "//commons.wikimedia.org/wiki/File:Commons_Museum.jpg",
          preferred: { url: "https://upload.wikimedia.org/commons-museum.jpg" },
        }), { status: 200, headers: { "content-type": "application/json" } });
      }
      if (url.includes("File%3AMissing.jpg")) return new Response("", { status: 404 });
      if (url.includes("File%3ATimeout.jpg")) throw new Error("request timed out");
      if (url.includes("ru.wikipedia.org/api/rest_v1/page/summary")) {
        wikipediaCalls += 1;
        return new Response(JSON.stringify({
          thumbnail: { source: "https://upload.wikimedia.org/wikipedia-place.jpg" },
          content_urls: { desktop: { page: "https://ru.wikipedia.org/wiki/Историческое_место" } },
        }), { status: 200, headers: { "content-type": "application/json" } });
      }
      throw new Error(`Unexpected URL: ${url}`);
    };
    try {
      const client = new OsmNearbyClient(
        "https://overpass.example.test",
        "https://nominatim.example.test",
        1_000,
      );
      const anchor: NearbyAnchor = {
        id: "hotel-1",
        type: "hotel",
        name: "Отель",
        latitude: 55.75,
        longitude: 37.61,
      };
      const first = await client.nearby(findCity("moscow")!, anchor, { includePointsOfInterest: true });
      const second = await client.nearby(findCity("moscow")!, anchor, { includePointsOfInterest: true });
      assert.equal(first.data.find((place) => place.name === "Commons музей")?.image?.source, "Wikimedia Commons");
      assert.equal(first.data.find((place) => place.name === "Wikipedia место")?.image?.source, "Wikipedia");
      assert.equal(first.data.find((place) => place.name === "Непроверенная картинка")?.image, undefined);
      assert.equal(first.data.find((place) => place.name === "Нет файла")?.image, undefined);
      assert.equal(first.data.find((place) => place.name === "Таймаут")?.image, undefined);
      assert.equal(first.data.find((place) => place.name === "Без тега изображения")?.image, undefined);
      assert.equal(first.data.length, second.data.length);
      assert.deepEqual({ commonsCalls, wikipediaCalls }, { commonsCalls: 1, wikipediaCalls: 1 });
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("keeps the trip usable when the weather source fails", async () => {
    const compiler = new TripCompiler(new EventfulProvider(), editorial, {
      forTrip: async () => {
        throw new Error("weather offline");
      },
    });

    const compiled = await compiler.compile("run-weather-failure", brief, profile);
    const proposal = compiled.proposals[0]!;

    assert.deepEqual(proposal.weather.days, []);
    assert.equal(
      proposal.sources.find((source) => source.component === "weather")?.availability,
      "unavailable",
    );
    assert.match(proposal.warnings.join(" "), /погода.+недоступна/iu);
  });

  it("never calls the demo provider from auto mode", async () => {
    let demoCalled = false;
    const real = new FlexibleProvider();
    real.flights = async () => {
      throw new Error("live source unavailable");
    };
    const demo = new FlexibleProvider();
    demo.flights = async (...args) => {
      demoCalled = true;
      return FlexibleProvider.prototype.flights.call(demo, ...args);
    };
    const provider = new ResilientPlannerProvider(real, demo, "auto");
    await assert.rejects(
      () => provider.flights({} as City, {} as City, "2026-09-18", brief.travelers),
      /live source unavailable/u,
    );
    assert.equal(demoCalled, false);
  });

  it("checks all three flexible intervals and rejects a hotel below the cohort floor", async () => {
    const provider = new FlexibleProvider();
    const compiler = new TripCompiler(provider, editorial);
    const compiled = await compiler.compile(
      "run-1",
      {
        ...brief,
        time: {
          mode: "flexible",
          windowStart: "2026-09-01",
          windowEnd: "2026-09-30",
          nights: 4,
        },
      },
      profile,
    );
    assert.equal(provider.hotelWindows.length, 3);
    assert.ok(compiled.proposals.every((proposal) => proposal.startDate !== "2026-09-26"));
    assert.ok(compiled.proposals.every((proposal) => proposal.hotel.price.amount >= 48_000));
    assert.ok(compiled.proposals.every((proposal) => proposal.dataMode === "real"));
    assert.ok(compiled.proposals.every((proposal) => proposal.completeness === "partial"));
  });

  it("checks fixed-city windows in parallel and publishes the first complete combination immediately", async () => {
    const provider = new ParallelFixedCityProvider();
    const partials: TripProposal[] = [];
    const weatherStartedAfterPartial: boolean[] = [];
    const compiler = new TripCompiler(provider, editorial, {
      forTrip: async (_city, window) => {
        weatherStartedAfterPartial.push(partials.length > 0);
        return {
          data: { days: [] },
          warnings: [],
          available: false,
          source: "Тестовая погода",
          checkedAt: `${window.startDate}T10:00:00.000Z`,
        };
      },
    });
    let settled = false;
    const compiling = compiler.compile(
      "run-parallel-fixed",
      {
        ...brief,
        preferences: {
          destinationTags: [],
          activities: [],
          climate: { maxDayTemperatureC: 20, strength: "soft" },
          other: [],
        },
        time: {
          mode: "flexible",
          windowStart: "2026-09-01",
          windowEnd: "2026-09-30",
          nights: 4,
        },
      },
      profile,
      { partial: (proposal) => partials.push(proposal) },
    ).finally(() => {
      settled = true;
    });

    await waitForCondition(() => provider.flightCalls === 6 && provider.hotelCalls === 3);
    await waitForCondition(() => partials.length === 1);
    assert.equal(settled, false);
    assert.equal(partials[0]?.startDate, "2026-09-01");
    assert.deepEqual(weatherStartedAfterPartial, [true]);
    assert.equal(provider.maxActiveFlights, 6);
    assert.equal(provider.maxActiveHotels, 3);

    provider.releaseSlowWindows();
    const compiled = await compiling;
    assert.equal(compiled.proposals.length, 3);
    assert.equal(partials.length, 3);
    assert.equal(new Set(partials.map((proposal) => proposal.title)).size, partials.length);
    assert.ok(weatherStartedAfterPartial.every(Boolean));
  });

  it("keeps successful fixed-city windows when another window times out", async () => {
    const provider = new FlexibleProvider();
    provider.hotels = async (_city, window) => {
      provider.hotelWindows.push(window);
      if (window.startDate === "2026-09-01") {
        throw new Error("ReadTimeout: hotel search timed out");
      }
      const nights = Math.max(
        1,
        Math.round((Date.parse(window.endDate) - Date.parse(window.startDate)) / 86_400_000),
      );
      return result([{
        hotelId: `available-${window.startDate}`,
        name: "Доступный отель",
        stars: 4,
        priceRub: 7_000 * nights,
        source: "T-Bank Hotels",
        live: true,
        checkedAt: "2026-08-16T10:00:00.000Z",
      }], "T-Bank Hotels");
    };
    const compiled = await new TripCompiler(provider, editorial).compile(
      "run-partial-window-timeout",
      {
        ...brief,
        time: {
          mode: "flexible",
          windowStart: "2026-09-01",
          windowEnd: "2026-09-30",
          nights: 4,
        },
      },
      profile,
    );

    assert.ok(compiled.proposals.length > 0);
    assert.ok(compiled.proposals.every((proposal) => proposal.startDate !== "2026-09-01"));
    assert.match(compiled.warnings.join(" "), /2026-09-01.*ReadTimeout/u);
  });

  it("reports failures from every fixed-city window when none succeeds", async () => {
    const provider = new FlexibleProvider();
    provider.hotels = async (_city, window) => {
      provider.hotelWindows.push(window);
      throw new Error(`ReadTimeout ${window.startDate}`);
    };
    let failure: unknown;
    try {
      await new TripCompiler(provider, editorial).compile(
        "run-all-window-timeouts",
        {
          ...brief,
          time: {
            mode: "flexible",
            windowStart: "2026-09-01",
            windowEnd: "2026-09-30",
            nights: 4,
          },
        },
        profile,
      );
    } catch (error) {
      failure = error;
    }

    assert.ok(failure instanceof Error);
    assert.equal(provider.hotelWindows.length, 3);
    for (const window of provider.hotelWindows) {
      assert.match(failure.message, new RegExp(window.startDate, "u"));
    }
  });

  it("does not offer a cheap motel to a client from a high-income cohort", async () => {
    const provider = new FlexibleProvider();
    provider.hotels = async (_city, window) => {
      const nights = Math.max(
        1,
        Math.round((Date.parse(window.endDate) - Date.parse(window.startDate)) / 86_400_000),
      );
      return result(
        [2_000, 7_000, 12_000, 24_000].map((nightlyPriceRub, index) => ({
          hotelId: `wealth-hotel-${index}`,
          name: `Отель ${index}`,
          stars: Math.min(5, 2 + index),
          priceRub: nightlyPriceRub * nights,
          latitude: 55.75,
          longitude: 37.61,
          source: "T-Bank Hotels",
          live: true,
          checkedAt: "2026-08-16T10:00:00.000Z",
        })),
        "T-Bank Hotels",
      );
    };
    const compiler = new TripCompiler(provider, editorial);
    const compiled = await compiler.compile(
      "run-high-income",
      brief,
      {
        ...profile,
        estimatedMonthlyIncomeRub: 500_000,
        incomeCohort: "200k_to_500k",
      },
    );

    assert.deepEqual(
      compiled.proposals.map((proposal) => proposal.hotel.price.amount / 3),
      [7_000, 12_000, 24_000],
    );
    assert.deepEqual(
      compiled.proposals.map((proposal) => proposal.tier),
      ["cohort_floor", "cohort_typical", "cohort_ceiling"],
    );
  });

  it("deduplicates concurrent hotel autocomplete and caches the resolved destination", async () => {
    const calls = { autocomplete: 0, search: 0 };
    const fakeMcp = {
      async callJson<T>(name: string): Promise<McpJsonResult<T>> {
        if (name === "hotel_autocomplete") {
          calls.autocomplete += 1;
          return mcpResult(
            { query: "Сочи", suggestions: [{ kind: "location", id: "42", name: "Сочи", signature: "", type: "" }] },
            "T-Bank Hotels",
          ) as unknown as McpJsonResult<T>;
        }
        if (name === "hotel_search") {
          calls.search += 1;
          return mcpResult(
            {
              hotels: [{ hotelId: "hotel-42", name: "Отель Сочи", stars: 4, price: 18_000, imageUrl: "https://cdn.tbank.ru/hotel.jpg" }],
              total: 1,
              isLoadingCompleted: true,
            },
            "T-Bank Hotels",
          ) as unknown as McpJsonResult<T>;
        }
        throw new Error(`Unexpected tool: ${name}`);
      },
      close: async () => undefined,
    };
    const provider = new TbankPlannerProvider(
      fakeMcp as unknown as TbankMcpClient,
      new OsmNearbyClient("https://overpass.example.test", "https://nominatim.example.test", 1_000),
      5_000,
    );
    const city = findCity("sochi")!;
    const [hotels] = await Promise.all([
      provider.hotels(city, { startDate: "2026-08-30", endDate: "2026-09-02" }, brief.travelers),
      provider.hotels(city, { startDate: "2026-09-06", endDate: "2026-09-09" }, brief.travelers),
      provider.hotels(city, { startDate: "2026-09-13", endDate: "2026-09-16" }, brief.travelers),
    ]);
    assert.deepEqual(calls, { autocomplete: 1, search: 3 });
    assert.equal(hotels?.data[0]?.image?.url, "https://cdn.tbank.ru/hotel.jpg");
  });

  it("does not retry a hotel search after ReadTimeout", async () => {
    const calls = { autocomplete: 0, search: 0 };
    const fakeMcp = {
      async callJson<T>(name: string): Promise<McpJsonResult<T>> {
        if (name === "hotel_autocomplete") {
          calls.autocomplete += 1;
          return mcpResult(
            { query: "Сочи", suggestions: [{ kind: "location", id: "42", name: "Сочи", signature: "", type: "" }] },
            "T-Bank Hotels",
          ) as unknown as McpJsonResult<T>;
        }
        if (name === "hotel_search") {
          calls.search += 1;
          throw new Error("ReadTimeout: HTTPSConnectionPool read timeout=30");
        }
        throw new Error(`Unexpected tool: ${name}`);
      },
      close: async () => undefined,
    };
    const provider = new TbankPlannerProvider(
      fakeMcp as unknown as TbankMcpClient,
      new OsmNearbyClient("https://overpass.example.test", "https://nominatim.example.test", 1_000),
      5_000,
    );
    await assert.rejects(
      provider.hotels(
        findCity("sochi")!,
        { startDate: "2026-08-30", endDate: "2026-09-02" },
        brief.travelers,
      ),
      /ReadTimeout/u,
    );
    assert.deepEqual(calls, { autocomplete: 1, search: 1 });
  });

  it("uses the dedicated slow-provider timeout for flight search", async () => {
    let receivedTimeout = 0;
    const fakeMcp = {
      async callJson<T>(name: string, _args: unknown, _schema: unknown, timeoutMs: number): Promise<McpJsonResult<T>> {
        assert.equal(name, "flight_search");
        receivedTimeout = timeoutMs;
        return mcpResult(
          {
            fromCode: "LED",
            toCode: "AER",
            date: "2026-08-30",
            searchId: "search-1",
            complete: true,
            offers: [{
              offerId: "offer-1",
              price: 12_300,
              currency: "RUB",
              summary: "LED → AER",
              departureAt: "2026-08-30T09:00:00",
              arrivalAt: "2026-08-30T13:00:00",
              withBaggage: false,
              refundable: false,
              vendor: "Tinkoff",
              legs: [],
            }],
          },
          "T-Bank Avia",
        ) as unknown as McpJsonResult<T>;
      },
      close: async () => undefined,
    };
    const provider = new TbankPlannerProvider(
      fakeMcp as unknown as TbankMcpClient,
      new OsmNearbyClient("https://overpass.example.test", "https://nominatim.example.test", 1_000),
      35_000,
      45_000,
    );
    const flights = await provider.flights(
      findCity("saint-petersburg")!,
      findCity("sochi")!,
      "2026-08-30",
      brief.travelers,
    );
    assert.equal(receivedTimeout, 45_000);
    assert.equal(flights.data[0]?.offerId, "offer-1");
  });

  it("keeps a partial bank profile without exposing a failed account id", async () => {
    const fakeMcp = {
      async callJson<T>(name: string, args: Record<string, unknown>): Promise<McpJsonResult<T>> {
        if (name === "list_accounts") {
          return mcpResult({
            accounts: [
              { id: "SAFE-1", name: "Основной", type: "Debit", status: "open", currency: "RUB" },
              { id: "SECRET-ACCOUNT-2", name: "Архивный", type: "Debit", status: "open", currency: "RUB" },
            ],
          }, "T-Bank") as unknown as McpJsonResult<T>;
        }
        if (name === "spending_categories") {
          if (args.account_id === "SECRET-ACCOUNT-2") throw new Error("NO_SUCH_ACCOUNT: SECRET-ACCOUNT-2");
          return mcpResult({
            totalSpent: 30_000,
            totalEarned: 450_000,
            categories: [
              { name: "Рестораны", amount: 9_000, count: 3 },
              { name: "Супермаркеты", amount: 6_000, count: 4 },
            ],
          }, "T-Bank") as unknown as McpJsonResult<T>;
        }
        if (name === "list_operations") {
          if (args.account_id === "SECRET-ACCOUNT-2") throw new Error("NO_SUCH_ACCOUNT: SECRET-ACCOUNT-2");
          return mcpResult({
            operations: [
              { id: "op-1", occurredAt: "2026-08-01", type: "Debit", amount: -3_000, currency: "RUB", description: "Суши кафе", category: "Рестораны" },
              { id: "op-2", occurredAt: "2026-08-02", type: "Debit", amount: -1_000, currency: "RUB", description: "Кофейня", category: "Рестораны" },
              { id: "op-3", occurredAt: "2026-08-03", type: "Debit", amount: -2_000, currency: "RUB", description: "Супермаркет", category: "Супермаркеты" },
            ],
            total: 3,
            hasMore: false,
          }, "T-Bank") as unknown as McpJsonResult<T>;
        }
        if (name === "orders") return mcpResult({
          orders: [{
            orderId: "order-event-1",
            objectType: "concert",
            status: "DONE",
            amount: 4_000,
            createdAt: "2026-07-01T10:00:00+03:00",
            title: "Инди-концерт",
            eventName: "Инди-концерт",
            hotelName: "",
            destination: "Москва",
          }],
        }, "T-Bank") as unknown as McpJsonResult<T>;
        if (name === "order_details") return mcpResult({
          orderId: "order-event-1",
          status: "DONE",
          createdAt: "2026-07-01T10:00:00+03:00",
          eventName: "Инди-концерт",
          genres: ["инди"],
          venue: "Клуб",
          address: "Центр",
          startDateTime: "2026-07-05T20:00:00+03:00",
          hallName: "Зал",
          seatCount: 1,
          ticketPricesRub: [4_000],
          totalAmountRub: 4_000,
        }, "T-Bank") as unknown as McpJsonResult<T>;
        if (name === "audience_profile") return mcpResult({
          ageBand: "25_34",
          adultContentAllowed: true,
        }, "T-Bank") as unknown as McpJsonResult<T>;
        if (name === "flight_history") return mcpResult({ searches: [] }, "T-Bank") as unknown as McpJsonResult<T>;
        throw new Error(`Unexpected tool: ${name}`);
      },
      close: async () => undefined,
    };
    const provider = new TbankPlannerProvider(
      fakeMcp as unknown as TbankMcpClient,
      new OsmNearbyClient("https://overpass.example.test", "https://nominatim.example.test", 1_000),
      35_000,
      45_000,
      5 * 60_000,
      () => Date.parse("2026-08-17T12:00:00.000Z"),
    );
    const bankProfile = await provider.profile();
    assert.equal(bankProfile.data.source, "bank");
    assert.equal(bankProfile.data.monthlySpendRub, 10_000);
    assert.equal(bankProfile.data.estimatedMonthlyIncomeRub, 150_000);
    assert.equal(bankProfile.data.incomeCohort, "100k_to_200k");
    assert.equal(bankProfile.data.incomeConfidence, "low");
    assert.equal(bankProfile.data.averageCheckRub, 2_000);
    assert.equal(bankProfile.data.medianCheckRub, 2_000);
    assert.equal(bankProfile.data.weekendAverageDailySpendRub, 154);
    assert.deepEqual(bankProfile.data.diningProfile.preferredCuisines, ["японская"]);
    assert.deepEqual(bankProfile.data.diningProfile.preferredVenueTypes, ["кафе и кофейни", "рестораны"]);
    assert.deepEqual(bankProfile.data.favoriteDiningMerchants, []);
    assert.equal(bankProfile.data.behavioralInsights?.events.purchaseCount, 1);
    assert.deepEqual(
      bankProfile.data.behavioralInsights?.events.genreAffinities.map((item) => item.value),
      ["инди"],
    );
    assert.equal(bankProfile.data.behavioralInsights?.audience.ageBand, "25_34");
    assert.doesNotMatch(JSON.stringify(bankProfile.data), /Суши кафе|Кофейня|Супермаркет"/u);
    assert.match(bankProfile.warnings.join(" "), /часть/iu);
    assert.doesNotMatch(bankProfile.warnings.join(" "), /SECRET-ACCOUNT-2/u);
  });

  it("refreshes only nearby groups for a restaurant chat change", async () => {
    const store = new TravelStore(":memory:");
    const provider = new CountingDemoProvider();
    const agent = new TravelPlannerAgent(
      store,
      provider,
      editorial,
    );
    try {
      const accepted = agent.createRun(brief);
      await waitForJob(store, accepted.jobId);
      const run = store.getRun(accepted.runId!);
      const proposal = run?.trips[0] as TripProposal;
      const trip = store.getTrip(proposal.id)!;
      provider.calls = { profile: 0, flights: 0, hotels: 0, events: 0, nearby: 0 };
      const change = agent.postMessage(trip.id, {
        text: "Больше ресторанов",
        baseRevisionId: trip.latestRevision.id,
      });
      await waitForJob(store, change.jobId);
      assert.deepEqual(provider.calls, { profile: 0, flights: 0, hotels: 0, events: 0, nearby: 2 });
      const updated = store.getTrip(trip.id)!;
      assert.equal(updated.revisionCount, 2);
      assert.match(updated.latestRevision.changeSummary?.join(" ") ?? "", /рестораны/u);
    } finally {
      store.close();
    }
  });

  it("executes an LLM cheaper-hotel plan by replacing only the hotel", async () => {
    const store = new TravelStore(":memory:");
    const provider = new FlexibleProvider();
    const baseHotels = provider.hotels.bind(provider);
    let exposeCheaperHotel = false;
    provider.hotels = async (...args) => {
      const response = await baseHotels(...args);
      if (!exposeCheaperHotel) return response;
      const current = response.data[0]!;
      return {
        ...response,
        data: [
          current,
          {
            ...current,
            hotelId: `${current.hotelId}-cheaper`,
            name: "Отель подешевле",
            priceRub: current.priceRub - 12_000,
          },
        ],
      };
    };
    const agent = new TravelPlannerAgent(
      store,
      provider,
      {
        decorate: async (proposals) => ({ proposals }),
        interpretChange: async (text) => ({
          action: "replace_hotel",
          hotelPreference: "cheaper",
          instructions: text,
        }),
      },
    );
    try {
      const accepted = agent.createRun(brief);
      await waitForJob(store, accepted.jobId);
      const initial = store.getRun(accepted.runId!)?.trips[0];
      assert.ok(initial);
      exposeCheaperHotel = true;

      const change = agent.postMessage(initial.id, {
        text: "Давай отель подешевле",
        baseRevisionId: store.getTrip(initial.id)!.latestRevision.id,
      });
      await waitForJob(store, change.jobId);

      const updated = store.getTrip(initial.id)!.latestRevision;
      assert.equal(updated.proposal.hotel.name, "Отель подешевле");
      assert.ok(updated.proposal.hotel.price.amount < initial.hotel.price.amount);
      assert.deepEqual(updated.proposal.flights, initial.flights);
      assert.deepEqual(updated.proposal.events, initial.events);
      assert.match(updated.changeSummary?.join(" ") ?? "", /Стоимость отеля/u);
    } finally {
      store.close();
    }
  });

  it("executes an LLM date-change plan and rebuilds the trip", async () => {
    const store = new TravelStore(":memory:");
    const provider = new FlexibleProvider();
    const agent = new TravelPlannerAgent(
      store,
      provider,
      {
        decorate: async (proposals) => ({ proposals }),
        interpretChange: async (text) => ({
          action: "change_dates",
          startDate: "2026-09-01",
          endDate: "2026-09-04",
          instructions: text,
        }),
      },
    );
    try {
      const accepted = agent.createRun({
        ...brief,
        time: { mode: "exact", startDate: "2026-08-21", endDate: "2026-08-24" },
      });
      await waitForJob(store, accepted.jobId);
      const initial = store.getRun(accepted.runId!)?.trips[0];
      assert.ok(initial);

      const change = agent.postMessage(initial.id, {
        text: "Хочу не 21 августа, а в начале сеньтября",
        baseRevisionId: store.getTrip(initial.id)!.latestRevision.id,
      });
      await waitForJob(store, change.jobId);

      const updated = store.getTrip(initial.id)!.latestRevision;
      assert.equal(updated.proposal.startDate, "2026-09-01");
      assert.equal(updated.proposal.endDate, "2026-09-04");
      assert.deepEqual(updated.brief.time, {
        mode: "exact",
        startDate: "2026-09-01",
        endDate: "2026-09-04",
      });
      assert.match(updated.changeSummary?.join(" ") ?? "", /Изменены даты/u);
    } finally {
      store.close();
    }
  });

  it("keeps images when hotel and event replacements create saved revisions", async () => {
    const store = new TravelStore(":memory:");
    const provider = new EventfulProvider();
    const baseHotels = provider.hotels.bind(provider);
    provider.hotels = async (...args) => {
      const response = await baseHotels(...args);
      const first = response.data[0]!;
      return {
        ...response,
        data: [
          first,
          {
            ...first,
            hotelId: `${first.hotelId}-alternative`,
            name: "Альтернативный отель",
            image: {
              url: "https://cdn.tbank.ru/hotel-alternative.jpg",
              source: "T-Bank Hotels",
            },
          },
        ],
      };
    };
    const replacementEditorial: EditorialService = {
      decorate: async (proposals) => ({ proposals }),
      interpretChange: async (text) => ({
        action: text.includes("отель") ? "replace_hotel" : "replace_event",
        instructions: text,
      }),
    };
    const agent = new TravelPlannerAgent(store, provider, replacementEditorial);
    try {
      const accepted = agent.createRun(brief);
      await waitForJob(store, accepted.jobId);
      const initial = store.getRun(accepted.runId!)?.trips[0];
      assert.ok(initial);

      const hotelChange = agent.postMessage(initial.id, {
        text: "Другой отель",
        baseRevisionId: store.getTrip(initial.id)!.latestRevision.id,
      });
      await waitForJob(store, hotelChange.jobId);
      const afterHotel = store.getTrip(initial.id)!;
      assert.notEqual(afterHotel.latestRevision.proposal.hotel.hotelId, initial.hotel.hotelId);
      assert.deepEqual(afterHotel.latestRevision.proposal.events, initial.events);
      assert.equal(
        afterHotel.latestRevision.proposal.hotel.mapPoint.image?.url,
        afterHotel.latestRevision.proposal.hotel.image?.url,
      );
      const initialHotelGroup = initial.restaurantGroups.find((group) => group.anchorType === "hotel")!;
      const nextHotelGroup = afterHotel.latestRevision.proposal.restaurantGroups.find((group) => group.anchorType === "hotel")!;
      assert.notEqual(nextHotelGroup.anchorId, initialHotelGroup.anchorId);
      assert.notDeepEqual(
        nextHotelGroup.restaurants.map((restaurant) => restaurant.osmId),
        initialHotelGroup.restaurants.map((restaurant) => restaurant.osmId),
      );
      assert.deepEqual(
        afterHotel.latestRevision.proposal.restaurantGroups
          .filter((group) => group.anchorType === "event"),
        initial.restaurantGroups.filter((group) => group.anchorType === "event"),
      );

      const eventChange = agent.postMessage(initial.id, {
        text: "Другие события",
        baseRevisionId: afterHotel.latestRevision.id,
      });
      await waitForJob(store, eventChange.jobId);
      const afterEvents = store.getTrip(initial.id)!;
      assert.equal(afterEvents.revisionCount, 3);
      assert.ok(afterEvents.latestRevision.proposal.events.length > 0);
      assert.ok(afterEvents.latestRevision.proposal.events.every((event) => event.image));
      assert.ok(afterEvents.latestRevision.proposal.events.every((event) => event.mapPoint?.image));
    } finally {
      store.close();
    }
  });

  it("changes only the outbound flight when the LLM asks for an earlier arrival", async () => {
    const store = new TravelStore(":memory:");
    const provider = new FlexibleProvider();
    const searches = { outbound: 0, returning: 0 };
    provider.flights = async (from, to, date) => {
      if (from.id === "saint-petersburg") {
        searches.outbound += 1;
        return result([{
          offerId: "late-outbound",
          summary: `${from.iata} → ${to.iata} поздний`,
          departureTime: "21:25",
          arrivalTime: "22:55",
          priceRub: 3_000,
          source: "T-Bank Avia",
          live: true,
          checkedAt: "2026-08-20T10:00:00.000Z",
        }, {
          offerId: "early-outbound",
          summary: `${from.iata} → ${to.iata} ранний`,
          departureTime: "16:50",
          arrivalTime: "18:20",
          priceRub: 4_500,
          source: "T-Bank Avia",
          live: true,
          checkedAt: "2026-08-20T10:00:00.000Z",
        }], "T-Bank Avia");
      }
      searches.returning += 1;
      return result([{
        offerId: "current-return",
        summary: `${from.iata} → ${to.iata}`,
        departureTime: "10:25",
        arrivalTime: "11:55",
        priceRub: 4_000,
        source: "T-Bank Avia",
        live: true,
        checkedAt: "2026-08-20T10:00:00.000Z",
      }], "T-Bank Avia");
    };
    const flightEditorial: EditorialService = {
      decorate: async (proposals) => ({ proposals }),
      interpretChange: async (text) => ({
        action: "replace_flight",
        flightDirection: "outbound",
        flightPreference: "earlier_arrival",
        instructions: text,
      }),
    };
    const agent = new TravelPlannerAgent(store, provider, flightEditorial);
    try {
      const accepted = agent.createRun(brief);
      await waitForJob(store, accepted.jobId);
      const initial = store.getRun(accepted.runId!)?.trips[0];
      assert.ok(initial);
      assert.equal(initial.flights.outbound.offerId, "late-outbound");
      assert.equal(initial.flights.outbound.arrivalTime, "22:55");
      const initialReturnId = initial.flights.return.offerId;
      searches.outbound = 0;
      searches.returning = 0;

      const change = agent.postMessage(initial.id, {
        text: "Хочу пораньше прилететь в Москву",
        baseRevisionId: store.getTrip(initial.id)!.latestRevision.id,
      });
      await waitForJob(store, change.jobId);

      const updated = store.getTrip(initial.id)!.latestRevision;
      assert.equal(updated.proposal.flights.outbound.offerId, "early-outbound");
      assert.equal(updated.proposal.flights.outbound.arrivalTime, "18:20");
      assert.equal(updated.proposal.flights.return.offerId, initialReturnId);
      assert.deepEqual(searches, { outbound: 1, returning: 0 });
      assert.match(updated.changeSummary?.join(" ") ?? "", /22:55 → 18:20/u);
    } finally {
      store.close();
    }
  });

  it("adds and removes trip events by date and by name", async () => {
    const store = new TravelStore(":memory:");
    const provider = new EventfulProvider();
    const eventEditorial: EditorialService = {
      decorate: async (proposals) => ({ proposals }),
      interpretChange: async (text) => {
        const changes: Record<string, Awaited<ReturnType<EditorialService["interpretChange"]>>> = {
          "Добавь событие на 21 сентября": {
            action: "add_event",
            eventDate: "2026-09-21",
            instructions: text,
          },
          "Убери «Концерт 4»": {
            action: "remove_event",
            eventName: "Концерт 4",
            instructions: text,
          },
          "Добавь событие «Концерт 5»": {
            action: "add_event",
            eventName: "Концерт 5",
            instructions: text,
          },
          "Удали события на 22.09.2026": {
            action: "remove_event",
            eventDate: "2026-09-22",
            instructions: text,
          },
        };
        const change = changes[text];
        if (!change) throw new Error(`Unexpected chat text: ${text}`);
        return change;
      },
    };
    const agent = new TravelPlannerAgent(
      store,
      provider,
      eventEditorial,
    );
    try {
      const accepted = agent.createRun({
        ...brief,
        time: { mode: "exact", startDate: "2026-09-18", endDate: "2026-09-24" },
      });
      await waitForJob(store, accepted.jobId);
      const initial = store.getRun(accepted.runId!)?.trips[0];
      assert.ok(initial);

      const send = async (text: string) => {
        const trip = store.getTrip(initial.id)!;
        const change = agent.postMessage(initial.id, {
          text,
          baseRevisionId: trip.latestRevision.id,
        });
        await waitForJob(store, change.jobId);
        return store.getTrip(initial.id)!.latestRevision.proposal;
      };

      const addedByDate = await send("Добавь событие на 21 сентября");
      assert.ok(addedByDate.events.some((event) =>
        event.name === "Концерт 4" && event.dateTime?.slice(0, 10) === "2026-09-21",
      ));
      assert.ok(addedByDate.restaurantGroups.some((group) => group.anchorId === "event-3"));

      const removedByName = await send("Убери «Концерт 4»");
      assert.ok(removedByName.events.every((event) => event.name !== "Концерт 4"));
      assert.ok(removedByName.restaurantGroups.every((group) => group.anchorId !== "event-3"));

      const addedByName = await send("Добавь событие «Концерт 5»");
      assert.ok(addedByName.events.some((event) => event.name === "Концерт 5"));

      const removedByDate = await send("Удали события на 22.09.2026");
      assert.ok(removedByDate.events.every((event) =>
        event.dateTime?.slice(0, 10) !== "2026-09-22",
      ));
      assert.equal(store.getTrip(initial.id)!.revisionCount, 5);
    } finally {
      store.close();
    }
  });

  it("replaces a rejected event with another event on the same day", async () => {
    const store = new TravelStore(":memory:");
    const provider = new SameDayReplacementProvider();
    const agent = new TravelPlannerAgent(
      store,
      provider,
      {
        decorate: async (proposals) => ({ proposals }),
        interpretChange: async (text) => ({
          action: "replace_event",
          eventName: "Русалочка. Любовь двух миров",
          eventDate: "2026-09-19",
          instructions: text,
        }),
      },
    );
    try {
      const accepted = agent.createRun({
        ...brief,
        time: { mode: "exact", startDate: "2026-09-18", endDate: "2026-09-24" },
      });
      await waitForJob(store, accepted.jobId);
      const initial = store.getRun(accepted.runId!)?.trips[0];
      assert.ok(initial);
      const rejected = initial.events.find((event) => event.name.startsWith("Русалочка"));
      assert.ok(rejected);

      const change = agent.postMessage(initial.id, {
        text: "Не хочу на русалочку, добавь что-то другое в этот день",
        baseRevisionId: store.getTrip(initial.id)!.latestRevision.id,
      });
      await waitForJob(store, change.jobId);

      const updated = store.getTrip(initial.id)!.latestRevision.proposal;
      const replacement = updated.events.find((event) => event.eventId === "event-1-alternative");
      assert.ok(replacement);
      assert.equal(replacement.dateTime?.slice(0, 10), rejected.dateTime?.slice(0, 10));
      assert.ok(updated.events.every((event) => event.eventId !== rejected.eventId));
      assert.ok(updated.restaurantGroups.some((group) => group.anchorId === replacement.eventId));
      assert.ok(updated.restaurantGroups.every((group) => group.anchorId !== rejected.eventId));
    } finally {
      store.close();
    }
  });

  it("still removes a rejected event when the same day has no alternative", async () => {
    const store = new TravelStore(":memory:");
    const provider = new EventfulProvider();
    const agent = new TravelPlannerAgent(
      store,
      provider,
      {
        decorate: async (proposals) => ({ proposals }),
        interpretChange: async (text) => ({
          action: "replace_event",
          eventName: "Концерт 2",
          eventDate: "2026-09-19",
          instructions: text,
        }),
      },
    );
    try {
      const accepted = agent.createRun({
        ...brief,
        time: { mode: "exact", startDate: "2026-09-18", endDate: "2026-09-24" },
      });
      await waitForJob(store, accepted.jobId);
      const initial = store.getRun(accepted.runId!)?.trips[0];
      assert.ok(initial);
      const rejected = initial.events.find((event) => event.name === "Концерт 2");
      assert.ok(rejected);

      const change = agent.postMessage(initial.id, {
        text: "Не хочу на концерт 2, добавь что-то другое в этот день",
        baseRevisionId: store.getTrip(initial.id)!.latestRevision.id,
      });
      await waitForJob(store, change.jobId);

      const revision = store.getTrip(initial.id)!.latestRevision;
      assert.ok(revision.proposal.events.every((event) => event.eventId !== rejected.eventId));
      assert.ok((revision.changeSummary?.join(" ") ?? "").toLocaleLowerCase("ru").includes("удалено"));
      assert.ok(revision.proposal.warnings.some((warning) =>
        warning.toLocaleLowerCase("ru").includes("другого подтверждённого события"),
      ));
    } finally {
      store.close();
    }
  });

  it("does not send merchant names, account ids or profile notes to LLM Proxy", async () => {
    const originalFetch = globalThis.fetch;
    let requestBody = "";
    globalThis.fetch = async (_input, init) => {
      requestBody += String(init?.body ?? "");
      return new Response(JSON.stringify({ error: { message: "fixture refusal" } }), {
        status: 400,
        headers: { "content-type": "application/json" },
      });
    };
    const provider = new FlexibleProvider();
    const privateProfile: PreferenceProfile = {
      ...profile,
      favoriteMerchants: ["SECRET_MERCHANT_FROM_OPERATION"],
      notes: ["SECRET_ACCOUNT_ID_123"],
    };
    try {
      const compiler = new TripCompiler(
        provider,
        new OpenAiEditorialService("test-key", "gpt-5.6-terra", 1_000),
      );
      const compiled = await compiler.compile("run-private", brief, privateProfile);
      assert.ok(requestBody, "The LLM Proxy adapter was not invoked");
      assert.doesNotMatch(requestBody, /SECRET_MERCHANT_FROM_OPERATION/u);
      assert.doesNotMatch(requestBody, /SECRET_ACCOUNT_ID_123/u);
      assert.match(requestBody, /monthlySpendRub/u);
      assert.doesNotMatch(compiled.warnings.join(" "), /fixture refusal|LLM Proxy/iu);
      assert.ok(compiled.proposals.every((proposal) =>
        proposal.sources.some((source) =>
          source.component === "editorial" &&
          source.availability === "available" &&
          source.source === "Локальный редактор",
        ),
      ));
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
