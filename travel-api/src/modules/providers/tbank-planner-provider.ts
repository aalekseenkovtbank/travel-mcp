import type { City, PreferenceProfile, TripBrief } from "@travel-growth-inspiration/contracts";
import type { ZodType } from "zod";

import type {
  DateWindow,
  EventInventoryItem,
  FlightInventoryItem,
  HotelInventoryItem,
  NearbyAnchor,
  NearbyPlace,
  NearbyPlacesProvider,
  NearbySearchOptions,
  PlannerDataProvider,
  ProviderResult,
} from "./provider-types.js";
import {
  accountsDataSchema,
  audienceProfileDataSchema,
  afishaCatalogDataSchema,
  concertScheduleDataSchema,
  flightHistoryDataSchema,
  flightSearchDataSchema,
  hotelAutocompleteDataSchema,
  hotelDetailsDataSchema,
  hotelSearchDataSchema,
  eventOrderDetailsDataSchema,
  operationsDataSchema,
  ordersDataSchema,
  spendingDataSchema,
  travelOrderDetailsDataSchema,
  type EventOrderDetailsData,
  type TravelOrderDetailsData,
} from "./tbank-json-contracts.js";
import { TbankMcpClient, type McpJsonResult } from "./tbank-mcp-client.js";
import { buildTransactionProfile, type CategoryAggregate, type ProfileOperation } from "./customer-profile.js";
import { buildBehavioralInsights, emptyBehavioralInsights } from "./behavioral-profile.js";

const INVENTORY_CACHE_TTL_MS = 5 * 60_000;

type HotelDestination = {
  id: number;
  source: string;
  checkedAt: string;
  warnings: string[];
};

function numeric(value: unknown): number {
  const number = typeof value === "number" ? value : Number(String(value ?? "").replace(",", "."));
  return Number.isFinite(number) ? number : 0;
}

function timeOf(value: string): string | undefined {
  const match = value.match(/T(\d{2}:\d{2})/u) ?? value.match(/\b(\d{2}:\d{2})\b/u);
  return match?.[1];
}

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

function isDiningCategory(value: string): boolean {
  return /ресторан|кафе|фастфуд|еда|столов|restaurant|cafe|fast.?food|dining/u.test(
    value.toLocaleLowerCase("ru"),
  );
}

function isInside(dateTime: string, window: DateWindow): boolean {
  const date = dateTime.slice(0, 10);
  return Boolean(date) && date >= window.startDate && date <= window.endDate;
}

function neutralProfile(warning: string): ProviderResult<PreferenceProfile> {
  const checkedAt = new Date().toISOString();
  return {
    data: {
      profileVersion: 2,
      generatedAt: checkedAt,
      source: "fallback",
      analysisWindowDays: 90,
      transactionCount: 0,
      estimatedMonthlyIncomeRub: 0,
      incomeCohort: "unknown",
      incomeConfidence: "unavailable",
      monthlySpendRub: 0,
      diningSpendRub: 0,
      weekendAverageDailySpendRub: 0,
      weekdayAverageDailySpendRub: 0,
      weekendSpendSharePct: 0,
      averageCheckRub: 0,
      medianCheckRub: 0,
      categoryBreakdown: [],
      diningProfile: {
        averageCheckRub: 0,
        medianCheckRub: 0,
        preferredCuisines: [],
        preferredVenueTypes: [],
      },
      shoppingProfile: {
        averageCheckRub: 0,
        medianCheckRub: 0,
        preferredStoreTypes: [],
      },
      preferredCategories: [],
      favoriteMerchants: [],
      favoriteDiningMerchants: [],
      eventInterests: [],
      previousDestinations: [],
      behavioralInsights: emptyBehavioralInsights(),
      llmSummary: "Банковский поведенческий профиль недоступен.",
      notes: ["Поиск выполняется без банковской персонализации."],
    },
    warnings: [warning],
    isFallback: true,
    source: "Нейтральный профиль",
    checkedAt,
  };
}

export class TbankPlannerProvider implements PlannerDataProvider {
  readonly dataMode = "real" as const;
  readonly #mcp: TbankMcpClient;
  readonly #nearbyPlaces: NearbyPlacesProvider;
  readonly #hotelTimeoutMs: number;
  readonly #flightTimeoutMs: number;
  readonly #inventoryCacheTtlMs: number;
  readonly #now: () => number;
  readonly #inventoryCache = new Map<string, {
    expiresAt: number;
    result: ProviderResult<unknown[]>;
  }>();
  readonly #inventoryInflight = new Map<string, Promise<ProviderResult<unknown[]>>>();
  readonly #hotelDestinations = new Map<string, HotelDestination>();
  readonly #hotelDestinationInflight = new Map<string, Promise<HotelDestination>>();

  constructor(
    mcp: TbankMcpClient,
    nearbyPlaces: NearbyPlacesProvider,
    hotelTimeoutMs = 35_000,
    flightTimeoutMs = 45_000,
    inventoryCacheTtlMs = INVENTORY_CACHE_TTL_MS,
    now: () => number = Date.now,
  ) {
    this.#mcp = mcp;
    this.#nearbyPlaces = nearbyPlaces;
    this.#hotelTimeoutMs = hotelTimeoutMs;
    this.#flightTimeoutMs = flightTimeoutMs;
    this.#inventoryCacheTtlMs = inventoryCacheTtlMs;
    this.#now = now;
  }

  async profile(): Promise<ProviderResult<PreferenceProfile>> {
    try {
      const accountsResult = await this.#mcp.callJson("list_accounts", {}, accountsDataSchema);
      const accountIds = accountsResult.data.accounts.map((account) => account.id).filter(Boolean).slice(0, 4);
      if (accountIds.length === 0) {
        return neutralProfile("Банк не вернул подходящих счетов; персонализация отключена.");
      }

      const [categorySettled, operationSettled, ordersResult, historyResult, audienceResult] = await Promise.all([
        Promise.allSettled(
          accountIds.map((accountId) =>
            this.#mcp.callJson(
              "spending_categories",
              { account_id: accountId, days: 90 },
              spendingDataSchema,
            ),
          ),
        ),
        Promise.allSettled(
          accountIds.map((accountId) =>
            this.#mcp.callJson(
              "list_operations",
              { account_id: accountId, days: 90, limit: 0, desc_len: 100 },
              operationsDataSchema,
            ),
          ),
        ),
        this.#mcp.callJson("orders", { kind: "", limit: 0 }, ordersDataSchema).catch(() => undefined),
        this.#mcp.callJson("flight_history", {}, flightHistoryDataSchema).catch(() => undefined),
        this.#mcp.callJson("audience_profile", {}, audienceProfileDataSchema).catch(() => undefined),
      ]);
      const categoryResults = categorySettled.flatMap((entry) =>
        entry.status === "fulfilled" ? [entry.value] : []);
      const operationResults = operationSettled.flatMap((entry) =>
        entry.status === "fulfilled" ? [entry.value] : []);
      if (categoryResults.length === 0 && operationResults.length === 0) {
        return neutralProfile("Банковские агрегаты временно недоступны; поиск продолжен без персонализации.");
      }

      const categoryTotals = new Map<string, number>();
      const categoryAggregates: CategoryAggregate[] = [];
      let total90 = 0;
      let earned90 = 0;
      let dining90 = 0;
      for (const result of categoryResults) {
        total90 += result.data.totalSpent;
        earned90 += result.data.totalEarned;
        for (const category of result.data.categories) {
          categoryTotals.set(category.name, (categoryTotals.get(category.name) ?? 0) + category.amount);
          categoryAggregates.push({ name: category.name, amount: category.amount });
          if (isDiningCategory(category.name)) {
            dining90 += category.amount;
          }
        }
      }

      const operations = operationResults.flatMap((result) => result.data.operations) as ProfileOperation[];
      const completeAccounts =
        categoryResults.length === accountIds.length &&
        operationResults.length === accountIds.length &&
        operationResults.every((result) => result.data.operations.length >= result.data.total);
      const transactionProfile = buildTransactionProfile({
        operations,
        categoryAggregates,
        totalSpent90Rub: total90,
        totalEarned90Rub: earned90,
        analysisWindowDays: 90,
        completeAccounts,
        nowMs: this.#now(),
      });

      const orderSignals = ordersResult?.data.orders ?? [];
      const eventOrderCandidates = orderSignals.filter((order) =>
        /concert|theatre|spectacle|movie|cinema|museum|exhibition|stand.?up|концерт|театр|спектак|кино|выстав|музе|стендап/iu
          .test(`${order.objectType} ${order.title} ${order.eventName}`),
      ).slice(0, 40);
      const hotelOrderCandidates = orderSignals.filter((order) =>
        /hotelbooking|hotel|отел|гостиниц/iu.test(`${order.objectType} ${order.title}`),
      ).slice(0, 20);
      const [eventDetailSettled, travelDetailSettled] = await Promise.all([
        Promise.allSettled(eventOrderCandidates.map((order) =>
          this.#mcp.callJson(
            "order_details",
            { order_id: order.orderId },
            eventOrderDetailsDataSchema,
          ))),
        Promise.allSettled(hotelOrderCandidates.map((order) =>
          this.#mcp.callJson(
            "travel_order_details",
            { order_id: order.orderId },
            travelOrderDetailsDataSchema,
          ))),
      ]);
      const eventDetails = eventDetailSettled.flatMap((entry) =>
        entry.status === "fulfilled" ? [entry.value.data] : []) as EventOrderDetailsData[];
      const travelDetails = travelDetailSettled.flatMap((entry) =>
        entry.status === "fulfilled" ? [entry.value.data] : []) as TravelOrderDetailsData[];
      const behavioralInsights = buildBehavioralInsights({
        operations,
        orders: orderSignals,
        eventDetails,
        travelDetails,
        ...(audienceResult ? { audience: audienceResult.data } : {}),
        analysisWindowDays: 90,
      });
      const eventInterests = behavioralInsights.events.kindAffinities.map((item) => item.value);
      const previousDestinations = unique([
        ...(historyResult?.data.searches.flatMap((search) => [search.to.name]) ?? []),
        ...orderSignals.map((order) => order.destination),
      ]).slice(0, 8);
      const checkedAt = new Date().toISOString();
      const warnings = unique([
        ...(categorySettled.some((entry) => entry.status === "rejected")
          ? ["Часть агрегатов трат недоступна и не учтена в персонализации."]
          : []),
        ...(operationSettled.some((entry) => entry.status === "rejected")
          ? ["Часть истории операций недоступна и не учтена в персонализации."]
          : []),
        ...accountsResult.warnings,
        ...categoryResults.flatMap((result) => result.warnings),
        ...operationResults.flatMap((result) => result.warnings),
        ...(ordersResult?.warnings ?? []),
        ...(historyResult?.warnings ?? []),
        ...(audienceResult?.warnings ?? []),
        ...(eventDetailSettled.some((entry) => entry.status === "rejected")
          ? ["Часть деталей прошлых заказов афиши недоступна и не учтена в предпочтениях."]
          : []),
        ...(travelDetailSettled.some((entry) => entry.status === "rejected")
          ? ["Часть деталей прошлых бронирований отелей недоступна и не учтена в предпочтениях."]
          : []),
      ]);
      return {
        data: {
          profileVersion: 2,
          generatedAt: checkedAt,
          source: "bank",
          analysisWindowDays: 90,
          transactionCount: transactionProfile.transactionCount,
          estimatedMonthlyIncomeRub: transactionProfile.estimatedMonthlyIncomeRub,
          incomeCohort: transactionProfile.incomeCohort,
          incomeConfidence: transactionProfile.incomeConfidence,
          monthlySpendRub: Math.round(total90 / 3),
          diningSpendRub: Math.round(dining90 / 3),
          weekendAverageDailySpendRub: transactionProfile.weekendAverageDailySpendRub,
          weekdayAverageDailySpendRub: transactionProfile.weekdayAverageDailySpendRub,
          weekendSpendSharePct: transactionProfile.weekendSpendSharePct,
          averageCheckRub: transactionProfile.averageCheckRub,
          medianCheckRub: transactionProfile.medianCheckRub,
          categoryBreakdown: transactionProfile.categoryBreakdown,
          diningProfile: transactionProfile.diningProfile,
          shoppingProfile: transactionProfile.shoppingProfile,
          preferredCategories: [...categoryTotals.entries()]
            .sort((left, right) => right[1] - left[1])
            .slice(0, 6)
            .map(([name]) => name),
          favoriteMerchants: [],
          favoriteDiningMerchants: [],
          eventInterests,
          previousDestinations,
          behavioralInsights,
          llmSummary: transactionProfile.llmSummary,
          notes: [
            "Профиль рассчитан локально; сырые операции и названия торговых точек не сохраняются и не передаются модели.",
            "Доход — оценка по внешним поступлениям за 90 дней, а не подтверждённая зарплата.",
            "Базовые траты в отпуске равны средним расходам за календарный выходной день.",
            "Из заказов сохраняются только агрегированные предпочтения: жанры, типы, площадки, время, ценовой уровень и состав группы.",
            "Точная дата рождения не сохраняется: используется только возрастной диапазон и допустимость 18+.",
          ],
        },
        warnings,
        isFallback: false,
        source: "T-Bank",
        checkedAt,
      };
    } catch (error) {
      return neutralProfile("Банковский профиль временно недоступен; поиск продолжен без персонализации.");
    }
  }

  async flights(
    from: City,
    to: City,
    date: string,
    travelers: TripBrief["travelers"],
  ): Promise<ProviderResult<FlightInventoryItem[]>> {
    const key = `flights:${from.id}:${to.id}:${date}:${this.#travelerKey(travelers)}`;
    return this.#cachedInventory(key, () => this.#loadFlights(from, to, date, travelers));
  }

  async #loadFlights(
    from: City,
    to: City,
    date: string,
    travelers: TripBrief["travelers"],
  ): Promise<ProviderResult<FlightInventoryItem[]>> {
    const result = await this.#mcp.callJson(
      "flight_search",
      {
        from_code: from.iata,
        to_code: to.iata,
        date,
        adults: travelers.adults,
        children: travelers.childrenAges.filter((age) => age >= 2).length,
        infants: travelers.childrenAges.filter((age) => age < 2).length,
        only_bookable: true,
        limit: 12,
      },
      flightSearchDataSchema,
      this.#flightTimeoutMs,
    );
    const flights = result.data.offers
      .filter((offer) => offer.offerId && offer.price > 0)
      .map((offer): FlightInventoryItem => {
        const departureTime = timeOf(offer.departureAt);
        const arrivalTime = timeOf(offer.arrivalAt);
        return {
          offerId: offer.offerId,
          summary: offer.summary || `${from.iata} → ${to.iata}`,
          priceRub: offer.price,
          ...(departureTime ? { departureTime } : {}),
          ...(arrivalTime ? { arrivalTime } : {}),
          source: result.source,
          live: true,
          checkedAt: result.checkedAt,
        };
      });
    return {
      data: flights,
      warnings: result.warnings,
      isFallback: false,
      source: result.source,
      checkedAt: result.checkedAt,
    };
  }

  async hotels(
    city: City,
    window: DateWindow,
    travelers: TripBrief["travelers"],
  ): Promise<ProviderResult<HotelInventoryItem[]>> {
    const key = `hotels:${city.id}:${window.startDate}:${window.endDate}:${this.#travelerKey(travelers)}`;
    return this.#cachedInventory(key, () => this.#loadHotels(city, window, travelers));
  }

  async #loadHotels(
    city: City,
    window: DateWindow,
    travelers: TripBrief["travelers"],
  ): Promise<ProviderResult<HotelInventoryItem[]>> {
    const destination = await this.#hotelDestination(city);
    const destinationId = destination.id;
    const autocompleteSource = destination.source;
    const autocompleteCheckedAt = destination.checkedAt;
    const autocompleteWarnings = destination.warnings;

    const byId = new Map<string, HotelInventoryItem>();
    const warnings = [...autocompleteWarnings];
    let source = autocompleteSource;
    let checkedAt = autocompleteCheckedAt;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const result = await this.#hotelCall(
        "hotel_search",
        {
          destination_id: destinationId,
          checkin_date: window.startDate,
          checkout_date: window.endDate,
          adults: travelers.adults,
          children_ages: travelers.childrenAges.join(","),
          limit: 50,
        },
        hotelSearchDataSchema,
      );
      source = result.source;
      checkedAt = result.checkedAt;
      warnings.push(...result.warnings);
      for (const hotel of result.data.hotels) {
        if (!hotel.hotelId || hotel.price <= 0) continue;
        byId.set(hotel.hotelId, {
          hotelId: hotel.hotelId,
          name: hotel.name || "Отель",
          stars: Math.max(0, Math.min(5, Math.round(hotel.stars))),
          priceRub: hotel.price,
          ...(hotel.address ? { address: hotel.address } : {}),
          ...(hotel.rating != null ? { rating: hotel.rating } : {}),
          ...(hotel.meal ? { meal: hotel.meal } : {}),
          ...(hotel.latitude != null ? { latitude: hotel.latitude } : {}),
          ...(hotel.longitude != null ? { longitude: hotel.longitude } : {}),
          ...(hotel.imageUrl
            ? { image: { url: hotel.imageUrl, source: result.source } }
            : {}),
          source: result.source,
          live: true,
          checkedAt: result.checkedAt,
        });
      }
      if (result.data.isLoadingCompleted || attempt === 2) break;
      await new Promise((resolve) => setTimeout(resolve, 250 * (attempt + 1)));
    }
    return {
      data: [...byId.values()].sort((left, right) => left.priceRub - right.priceRub),
      warnings: unique(warnings),
      isFallback: false,
      source,
      checkedAt,
    };
  }

  async events(
    city: City,
    window: DateWindow,
    interests: string[],
  ): Promise<ProviderResult<EventInventoryItem[]>> {
    const key = `events:${city.id}:${window.startDate}:${window.endDate}:${[...interests].sort().join("|")}`;
    return this.#cachedInventory(key, () => this.#loadEvents(city, window, interests));
  }

  async #loadEvents(
    city: City,
    window: DateWindow,
    interests: string[],
  ): Promise<ProviderResult<EventInventoryItem[]>> {
    const normalized = interests.join(" ").toLocaleLowerCase("ru");
    const kinds = unique([
      ...(/театр|спектак/u.test(normalized) ? ["театр"] : []),
      ...(/концерт|музык|рок|джаз/u.test(normalized) ? ["концерт"] : []),
      ...(/кино|фильм/u.test(normalized) ? ["кино"] : []),
      ...(/выстав|музе|искусств/u.test(normalized) ? ["выставка"] : []),
      "концерт",
      "театр",
      "выставка",
      "кино",
    ]).slice(0, 4);
    const results = await Promise.allSettled(
      kinds.map(async (kind) => ({
        kind,
        result: await this.#mcp.callJson(
          "afisha_catalog",
          {
            kind,
            city: city.name,
            date_from: window.startDate,
            date_to: window.endDate,
            limit: 15,
            pages: 4,
          },
          afishaCatalogDataSchema,
        ),
      })),
    );
    const warnings: string[] = [];
    const eventsById = new Map<string, {
      event: EventInventoryItem;
      kind: string;
      slotId: string;
    }>();
    const calendarDays = Math.max(1, Math.round((Date.parse(window.endDate) - Date.parse(window.startDate)) / 86_400_000) + 1);
    const scheduleLookupLimit = Math.max(4, Math.ceil(calendarDays / 3) * 2);
    let checkedAt = new Date().toISOString();
    for (const settled of results) {
      if (settled.status === "rejected") {
        warnings.push(`Афиша: ${settled.reason instanceof Error ? settled.reason.message : "источник недоступен"}`);
        continue;
      }
      const { kind, result } = settled.value;
      checkedAt = result.checkedAt;
      warnings.push(...result.warnings);
      for (const event of result.data.events) {
        const slot = event.slots.find((candidate) => isInside(candidate.startDateTime, window));
        if (!slot || !isInside(slot.startDateTime, window)) continue;
        const priceRub = slot.priceFix ?? slot.priceMin ?? slot.priceMax ?? undefined;
        if (eventsById.has(event.eventId)) continue;
        eventsById.set(event.eventId, {
          kind,
          slotId: slot.slotId,
          event: {
          eventId: event.eventId,
          name: event.name,
          kind,
          ...(event.genres.length ? { genres: event.genres } : {}),
          ...(event.ageRestriction ? { ageRestriction: event.ageRestriction } : {}),
          ...(event.rating !== undefined && event.rating !== null ? { rating: event.rating } : {}),
          dateTime: slot.startDateTime,
          ...(priceRub !== undefined && priceRub > 0 ? { priceRub } : {}),
          ...(event.imageUrl
            ? { image: { url: event.imageUrl, source: result.source } }
            : {}),
          source: result.source,
          checkedAt: result.checkedAt,
          },
        });
      }
    }

    const candidates = [...eventsById.values()].filter(({ kind }) => kind !== "кино");
    const interestSignals = interests
      .map((value) => value.toLocaleLowerCase("ru").replaceAll("ё", "е").trim())
      .filter(Boolean);
    const rankedCandidates = candidates.sort((left, right) => {
      const score = (candidate: typeof left) => {
        const text = [
          candidate.event.name,
          candidate.event.kind,
          ...(candidate.event.genres ?? []),
        ].join(" ").toLocaleLowerCase("ru").replaceAll("ё", "е");
        return interestSignals.reduce(
          (total, signal) => total + (text.includes(signal) || signal.includes(text) ? 100 : 0),
          0,
        ) + (candidate.event.rating ?? 0);
      };
      return score(right) - score(left) ||
        String(left.event.dateTime).localeCompare(String(right.event.dateTime));
    });
    const scheduleCandidates: typeof rankedCandidates = [];
    const scheduledIds = new Set<string>();
    const scheduledDays = new Set<string>();
    for (const candidate of rankedCandidates) {
      const day = candidate.event.dateTime?.slice(0, 10);
      if (!day || scheduledDays.has(day)) continue;
      scheduleCandidates.push(candidate);
      scheduledIds.add(candidate.event.eventId);
      scheduledDays.add(day);
      if (scheduleCandidates.length >= scheduleLookupLimit) break;
    }
    for (const candidate of rankedCandidates) {
      if (scheduleCandidates.length >= scheduleLookupLimit) break;
      if (scheduledIds.has(candidate.event.eventId)) continue;
      scheduleCandidates.push(candidate);
      scheduledIds.add(candidate.event.eventId);
    }

    const schedules = await Promise.allSettled(scheduleCandidates.map(async (candidate) => ({
      candidate,
      schedule: await this.#mcp.callJson(
        "concert_schedule",
        { event_id: candidate.event.eventId, kind: candidate.kind, limit: 8 },
        concertScheduleDataSchema,
      ),
    })));
    for (const settled of schedules) {
      if (settled.status === "rejected") {
        warnings.push(`Расписание события недоступно: ${settled.reason instanceof Error ? settled.reason.message : "ошибка источника"}`);
        continue;
      }
      const { candidate, schedule } = settled.value;
      warnings.push(...schedule.warnings);
      const showing = schedule.data.showings.find((item) =>
        item.slotId === candidate.slotId && isInside(item.startDateTime, window)) ??
        schedule.data.showings.find((item) =>
          item.startDateTime === candidate.event.dateTime && isInside(item.startDateTime, window));
      if (!showing) continue;
      candidate.event = {
        ...candidate.event,
        dateTime: showing.startDateTime,
        ...(showing.venue ? { venue: showing.venue } : {}),
        ...(showing.address ? { address: showing.address } : {}),
        ...(showing.latitude !== null && showing.latitude !== undefined
          ? { latitude: showing.latitude }
          : {}),
        ...(showing.longitude !== null && showing.longitude !== undefined
          ? { longitude: showing.longitude }
          : {}),
        ...((showing.priceFix ?? showing.priceMin ?? showing.priceMax) !== null &&
          (showing.priceFix ?? showing.priceMin ?? showing.priceMax) !== undefined
          ? { priceRub: (showing.priceFix ?? showing.priceMin ?? showing.priceMax)! }
          : {}),
      };
    }
    return {
      data: [...eventsById.values()].map(({ event }) => event),
      warnings: unique(warnings),
      isFallback: false,
      source: "T-Bank Afisha",
      checkedAt,
    };
  }

  async nearby(
    city: City,
    anchor: NearbyAnchor,
    options: NearbySearchOptions = {},
  ): Promise<ProviderResult<NearbyPlace[]>> {
    let resolvedAnchor = anchor;
    if (
      anchor.type === "hotel" &&
      (anchor.latitude === undefined || anchor.longitude === undefined || !anchor.address)
    ) {
      try {
        const details = await this.#hotelCall(
          "hotel_details",
          { hotel_id: anchor.id, max_facilities: 0 },
          hotelDetailsDataSchema,
        );
        resolvedAnchor = {
          ...anchor,
          ...(anchor.address || details.data.address
            ? { address: anchor.address || details.data.address }
            : {}),
          ...(anchor.latitude !== undefined || details.data.latitude != null
            ? { latitude: anchor.latitude ?? details.data.latitude! }
            : {}),
          ...(anchor.longitude !== undefined || details.data.longitude != null
            ? { longitude: anchor.longitude ?? details.data.longitude! }
            : {}),
        };
      } catch {
        // Nominatim remains the safe fallback when the public hotel card is incomplete.
      }
    }
    return this.#nearbyPlaces.nearby(city, resolvedAnchor, options);
  }

  async #hotelCall<T>(
    name: "hotel_autocomplete" | "hotel_search" | "hotel_details",
    args: Record<string, unknown>,
    schema: ZodType<T>,
  ): Promise<McpJsonResult<T>> {
    return this.#mcp.callJson(name, args, schema, this.#hotelTimeoutMs);
  }

  async #hotelDestination(city: City): Promise<HotelDestination> {
    const cached = this.#hotelDestinations.get(city.id);
    if (cached) return cached;
    const inflight = this.#hotelDestinationInflight.get(city.id);
    if (inflight) return inflight;
    const pending = this.#hotelCall(
      "hotel_autocomplete",
      { query: city.name, limit: 10 },
      hotelAutocompleteDataSchema,
    ).then((autocomplete): HotelDestination => {
      const suggestion =
        autocomplete.data.suggestions.find(
          (item) => item.kind === "location" && item.name === city.name,
        ) ?? autocomplete.data.suggestions.find((item) => item.kind === "location");
      const id = Number(suggestion?.id);
      if (!suggestion || !Number.isInteger(id) || id <= 0) {
        throw new Error(`Не найден hotel destination_id для города ${city.name}`);
      }
      const destination = {
        id,
        source: autocomplete.source,
        checkedAt: autocomplete.checkedAt,
        warnings: autocomplete.warnings,
      };
      this.#hotelDestinations.set(city.id, destination);
      return destination;
    }).finally(() => this.#hotelDestinationInflight.delete(city.id));
    this.#hotelDestinationInflight.set(city.id, pending);
    return pending;
  }

  #travelerKey(travelers: TripBrief["travelers"]): string {
    return `${travelers.adults}:${travelers.childrenAges.join(",")}`;
  }

  #cachedInventory<T>(
    key: string,
    load: () => Promise<ProviderResult<T[]>>,
  ): Promise<ProviderResult<T[]>> {
    const now = this.#now();
    const cached = this.#inventoryCache.get(key);
    if (cached && cached.expiresAt > now) {
      return Promise.resolve(cached.result as ProviderResult<T[]>);
    }
    if (cached) this.#inventoryCache.delete(key);
    const inflight = this.#inventoryInflight.get(key);
    if (inflight) return inflight as Promise<ProviderResult<T[]>>;
    const pending = load()
      .then((result) => {
        if (result.data.length > 0) {
          this.#inventoryCache.set(key, {
            expiresAt: this.#now() + this.#inventoryCacheTtlMs,
            result: result as ProviderResult<unknown[]>,
          });
        }
        return result;
      })
      .finally(() => this.#inventoryInflight.delete(key));
    this.#inventoryInflight.set(key, pending as Promise<ProviderResult<unknown[]>>);
    return pending;
  }

  async close(): Promise<void> {
    await this.#mcp.close();
  }
}
