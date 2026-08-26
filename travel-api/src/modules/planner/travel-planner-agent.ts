import { randomUUID } from "node:crypto";

import type {
  AsyncJobAccepted,
  EventOption,
  FlightOption,
  HotelOption,
  MapPoint,
  PreferenceProfile,
  Price,
  Restaurant,
  RestaurantGroup,
  SourceStatus,
  TripBrief,
  TripMessageInput,
  TripPace,
  TripProposal,
} from "@travel-growth-inspiration/contracts";

import { AppError } from "../../http/app-error.js";
import { findCity, findCityByName } from "../catalog/cities.js";
import type { EditorialService, TripChangeSet } from "../editorial/editorial-service.js";
import type {
  EventInventoryItem,
  FlightInventoryItem,
  HotelInventoryItem,
  NearbyAnchor,
  NearbyPlace,
  NearbySearchOptions,
  PlannerDataProvider,
  ProviderResult,
} from "../providers/provider-types.js";
import {
  UnavailableWeatherService,
  type WeatherService,
} from "../providers/open-meteo-weather-service.js";
import { TravelStore } from "../storage/travel-store.js";
import {
  eventSearchInterests,
  hotelNightlyPriceRange,
  nearbyPlaceKinds,
  selectTripEvents,
  targetEventCount,
  TripCompiler,
} from "./trip-compiler.js";

function message(error: unknown): string {
  return error instanceof Error ? error.message : "Неизвестная ошибка";
}

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

function normalizeSignal(value: string): string {
  return value
    .toLocaleLowerCase("ru")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function priceOf(item: FlightInventoryItem | HotelInventoryItem): Price {
  return {
    amount: item.priceRub,
    currency: "RUB",
    kind: item.live ? "live" : "estimated",
    source: item.source,
    checkedAt: item.checkedAt,
    ...(item.live
      ? { expiresAt: new Date(Date.parse(item.checkedAt) + 15 * 60_000).toISOString() }
      : {}),
  };
}

type FlightPreference = NonNullable<TripChangeSet["flightPreference"]>;
type FlightTiming = Pick<FlightInventoryItem | FlightOption, "departureTime" | "arrivalTime">;

function clockMinutes(value: string | undefined): number | undefined {
  if (!value) return undefined;
  const [hoursText, minutesText] = value.split(":");
  const hours = Number(hoursText);
  const minutes = Number(minutesText);
  if (
    !Number.isInteger(hours) || !Number.isInteger(minutes) ||
    hours < 0 || hours > 23 || minutes < 0 || minutes > 59
  ) return undefined;
  return hours * 60 + minutes;
}

function flightTimeMetric(flight: FlightTiming, preference: FlightPreference): number | undefined {
  const departure = clockMinutes(flight.departureTime);
  if (preference === "earlier_departure" || preference === "later_departure") return departure;
  const arrival = clockMinutes(flight.arrivalTime);
  if (arrival === undefined) return undefined;
  return departure !== undefined && arrival < departure ? arrival + 24 * 60 : arrival;
}

function sameFlight(item: FlightInventoryItem, current: FlightOption): boolean {
  if (item.offerId && current.offerId) return item.offerId === current.offerId;
  return item.summary === current.summary &&
    item.departureTime === current.departureTime &&
    item.arrivalTime === current.arrivalTime;
}

function chooseRevision(
  proposals: TripProposal[],
  current: TripProposal,
  change: TripChangeSet,
): TripProposal | undefined {
  if (change.action === "cheaper") {
    return [...proposals].sort((a, b) => a.totalPrice.amount - b.totalPrice.amount)[0];
  }
  if (change.action === "more_comfort") {
    return [...proposals].sort((a, b) => b.totalPrice.amount - a.totalPrice.amount)[0];
  }
  if (change.action === "replace_hotel") {
    return proposals.find((proposal) => proposal.hotel.hotelId !== current.hotel.hotelId) ?? proposals[0];
  }
  if (change.action === "replace_flight") {
    return (
      proposals.find(
        (proposal) => proposal.flights.outbound.offerId !== current.flights.outbound.offerId,
      ) ?? proposals[0]
    );
  }
  return proposals.find((proposal) => proposal.tier === current.tier) ?? proposals[0];
}

export class TravelPlannerAgent {
  readonly #store: TravelStore;
  readonly #provider: PlannerDataProvider;
  readonly #editorial: EditorialService;
  readonly #compiler: TripCompiler;

  constructor(
    store: TravelStore,
    provider: PlannerDataProvider,
    editorial: EditorialService,
    weather: WeatherService = new UnavailableWeatherService(),
  ) {
    this.#store = store;
    this.#provider = provider;
    this.#editorial = editorial;
    this.#compiler = new TripCompiler(provider, editorial, weather);
  }

  createRun(brief: TripBrief): AsyncJobAccepted {
    const runId = this.#store.createRun(brief, this.#provider.dataMode);
    const jobId = this.#store.createJob("compile", { runId });
    void this.#compileRun(runId, jobId, brief);
    return { runId, jobId };
  }

  postMessage(tripId: string, input: TripMessageInput): AsyncJobAccepted {
    const trip = this.#store.getTrip(tripId);
    if (!trip) throw new AppError(404, "TRIP_NOT_FOUND", "Поездка не найдена");
    if (trip.preparationStatus !== "ready") {
      throw new AppError(409, "TRIP_PREPARING", "Сначала дождитесь завершения подготовки поездки");
    }
    if (trip.latestRevision.id !== input.baseRevisionId) {
      throw new AppError(409, "STALE_TRIP_REVISION", "Поездка уже изменилась; обновите страницу");
    }
    const userMessage = this.#store.addMessage(tripId, "user", input.text);
    const jobId = this.#store.createJob("chat", { runId: trip.runId, tripId });
    void this.#processMessage(jobId, tripId, input.text);
    return { jobId, tripId, messageId: userMessage.id };
  }

  refresh(tripId: string): AsyncJobAccepted {
    const trip = this.#store.getTrip(tripId);
    if (!trip) throw new AppError(404, "TRIP_NOT_FOUND", "Поездка не найдена");
    if (trip.preparationStatus !== "ready") {
      throw new AppError(409, "TRIP_PREPARING", "Сначала дождитесь завершения подготовки поездки");
    }
    const jobId = this.#store.createJob("refresh", { runId: trip.runId, tripId });
    void this.#refreshTrip(jobId, tripId);
    return { jobId, tripId };
  }

  async #compileRun(runId: string, jobId: string, brief: TripBrief): Promise<void> {
    this.#store.updateJob(jobId, "running");
    this.#store.setRunStatus(runId, "running");
    this.#store.appendEvent(jobId, "job.started", { runId, dataMode: this.#provider.dataMode });
    try {
      const cachedProfile =
        this.#provider.dataMode === "real"
          ? this.#store.getLatestProfileSnapshot(24 * 60 * 60_000)
          : undefined;
      const profileResult = cachedProfile
        ? {
            data: cachedProfile,
            warnings: ["Использован банковский профиль, рассчитанный менее 24 часов назад."],
            isFallback: false,
            source: "Кеш профиля T-Bank",
            checkedAt: cachedProfile.generatedAt,
          }
        : await this.#provider.profile();
      const profile = profileResult.data;
      if (!cachedProfile && profile.source === "bank") this.#store.saveProfileSnapshot(profile);
      this.#store.setRunProfile(runId, profile);
      for (const warning of profileResult.warnings) this.#store.addRunWarning(runId, warning);
      this.#store.appendEvent(jobId, "profile.ready", {
        source: profile.source,
        incomeCohort: profile.incomeCohort,
        weekendAverageDailySpendRub: profile.weekendAverageDailySpendRub,
        averageCheckRub: profile.averageCheckRub,
        preferredCategories: profile.preferredCategories,
        eventInterests: profile.eventInterests,
        eventPurchaseCount: profile.behavioralInsights?.events.purchaseCount ?? 0,
        eventGenres: profile.behavioralInsights?.events.genreAffinities.slice(0, 5).map((item) => item.value) ?? [],
      });

      const result = await this.#compiler.compile(runId, brief, profile, {
        shortlist: (cityList) => {
          this.#store.appendEvent(jobId, "shortlist.ready", {
            cities: cityList.map((city) => ({ id: city.id, name: city.name })),
          });
        },
        candidate: (city, status) => {
          this.#store.appendEvent(jobId, "candidate.progress", {
            cityId: city.id,
            cityName: city.name,
            status,
          });
        },
        partial: (proposal) => {
          this.#store.createTrip(runId, proposal, brief);
          this.#store.appendEvent(jobId, "trip.partial", { proposal, stage: "core" });
        },
      });
      for (const warning of result.warnings) this.#store.addRunWarning(runId, warning);
      for (const proposal of result.proposals) {
        this.#store.finalizePreparingTrip(proposal.id, proposal);
        this.#store.appendEvent(jobId, "trip.ready", { proposal, stage: "enriched" });
      }
      const completeness =
        result.proposals.length < 3 || result.proposals.some((proposal) => proposal.completeness === "partial")
          ? "partial"
          : "complete";
      this.#store.setRunResultMetadata(runId, completeness, result.proposals[0]?.sources ?? []);
      this.#store.setRunStatus(runId, "completed");
      this.#store.updateJob(jobId, "completed");
      this.#store.appendEvent(jobId, "job.completed", {
        runId,
        tripCount: result.proposals.length,
        partial: result.proposals.length < 3,
      });
    } catch (error) {
      const errorText = message(error);
      this.#store.addRunWarning(runId, errorText);
      this.#store.setRunResultMetadata(runId, "failed", []);
      this.#store.setRunStatus(runId, "failed");
      this.#store.updateJob(jobId, "failed", errorText);
      this.#store.appendEvent(jobId, "job.failed", { runId, message: errorText });
    }
  }

  async #processMessage(jobId: string, tripId: string, text: string): Promise<void> {
    this.#store.updateJob(jobId, "running");
    this.#store.appendEvent(jobId, "job.started", { tripId, mode: "chat" });
    try {
      const trip = this.#store.getTrip(tripId);
      if (!trip) throw new Error("Поездка не найдена");
      const current = trip.latestRevision;
      const change = await this.#editorial.interpretChange(text, current.proposal);
      const brief = this.#applyChange(current.brief, current.proposal, change);
      const run = this.#store.getRun(trip.runId);
      const profile = run?.profile ?? (await this.#provider.profile()).data;
      const local = await this.#applyLocalChange(current.proposal, brief, change, profile);
      if (local) {
        const revision = this.#store.addRevision(
          tripId,
          brief,
          { ...local.proposal, id: tripId },
          local.changeSummary,
        );
        const response = this.#chatResponse(change, revision.proposal, local.warnings, local.changeSummary);
        this.#store.addMessage(tripId, "assistant", response, revision.id);
        this.#store.appendEvent(jobId, "trip.ready", {
          proposal: revision.proposal,
          revision,
          changeSummary: local.changeSummary,
        });
        this.#store.updateJob(jobId, "completed");
        this.#store.appendEvent(jobId, "job.completed", {
          tripId,
          revisionId: revision.id,
          changeSummary: local.changeSummary,
        });
        return;
      }
      const result = await this.#compiler.compile(trip.runId, brief, profile, {
        shortlist: (cityList) =>
          this.#store.appendEvent(jobId, "shortlist.ready", {
            cities: cityList.map((city) => ({ id: city.id, name: city.name })),
          }),
        candidate: (city, status) =>
          this.#store.appendEvent(jobId, "candidate.progress", {
            cityId: city.id,
            cityName: city.name,
            status,
          }),
      });
      const proposal = chooseRevision(result.proposals, current.proposal, change);
      if (!proposal) throw new Error("Не удалось собрать обновлённую поездку с такими условиями");
      const changeSummary = this.#fullChangeSummary(change);
      const revision = this.#store.addRevision(
        tripId,
        brief,
        { ...proposal, id: tripId },
        changeSummary,
      );
      const response = this.#chatResponse(change, revision.proposal, result.warnings, changeSummary);
      this.#store.addMessage(tripId, "assistant", response, revision.id);
      this.#store.appendEvent(jobId, "trip.ready", { proposal: revision.proposal, revision });
      this.#store.updateJob(jobId, "completed");
      this.#store.appendEvent(jobId, "job.completed", { tripId, revisionId: revision.id });
    } catch (error) {
      const errorText = message(error);
      this.#store.addMessage(
        tripId,
        "assistant",
        `Не получилось применить изменение: ${errorText}. Исходная версия поездки сохранена.`,
      );
      this.#store.updateJob(jobId, "failed", errorText);
      this.#store.appendEvent(jobId, "job.failed", { tripId, message: errorText });
    }
  }

  async #refreshTrip(jobId: string, tripId: string): Promise<void> {
    this.#store.updateJob(jobId, "running");
    this.#store.appendEvent(jobId, "job.started", { tripId, mode: "refresh" });
    try {
      const trip = this.#store.getTrip(tripId);
      if (!trip) throw new Error("Поездка не найдена");
      const run = this.#store.getRun(trip.runId);
      const profile: PreferenceProfile = run?.profile ?? (await this.#provider.profile()).data;
      const result = await this.#compiler.compile(
        trip.runId,
        trip.latestRevision.brief,
        profile,
      );
      const proposal = chooseRevision(result.proposals, trip.latestRevision.proposal, {
        action: "general",
        instructions: "Обновить цены",
      });
      if (!proposal) throw new Error("Не удалось обновить цены");
      const revision = this.#store.addRevision(
        tripId,
        trip.latestRevision.brief,
        { ...proposal, id: tripId },
        ["Повторно проверены рейсы, отель, события и места рядом"],
      );
      this.#store.addMessage(tripId, "assistant", "Цены и доступность перепроверены.", revision.id);
      this.#store.appendEvent(jobId, "trip.ready", { proposal: revision.proposal, revision });
      this.#store.updateJob(jobId, "completed");
      this.#store.appendEvent(jobId, "job.completed", { tripId, revisionId: revision.id });
    } catch (error) {
      const errorText = message(error);
      this.#store.updateJob(jobId, "failed", errorText);
      this.#store.appendEvent(jobId, "job.failed", { tripId, message: errorText });
    }
  }

  async #applyLocalChange(
    current: TripProposal,
    brief: TripBrief,
    change: TripChangeSet,
    profile: PreferenceProfile,
  ): Promise<
    | { proposal: TripProposal; warnings: string[]; changeSummary: string[] }
    | undefined
  > {
    if (change.action === "replace_hotel") return this.#replaceHotel(current, brief, profile, change);
    if (change.action === "replace_flight") return this.#replaceFlights(current, brief, change);
    if (change.action === "more_restaurants") return this.#refreshNearby(current, brief, profile);
    if (change.action === "replace_event") return this.#replaceEvent(current, brief, profile, change);
    if (change.action === "add_event") return this.#addEvent(current, brief, profile, change);
    if (change.action === "remove_event") return this.#removeEvent(current, brief, profile, change);
    return undefined;
  }

  async #replaceHotel(
    current: TripProposal,
    brief: TripBrief,
    profile: PreferenceProfile,
    change: TripChangeSet,
  ): Promise<{ proposal: TripProposal; warnings: string[]; changeSummary: string[] }> {
    const hotels = await this.#provider.hotels(
      current.destination,
      { startDate: current.startDate, endDate: current.endDate },
      brief.travelers,
    );
    const nights = Math.max(
      1,
      Math.round((Date.parse(current.endDate) - Date.parse(current.startDate)) / 86_400_000),
    );
    const range = hotelNightlyPriceRange(profile.incomeCohort);
    const positionTarget = {
      cohort_floor: range.minRub,
      cohort_typical: range.typicalRub,
      cohort_ceiling: range.maxRub,
    }[current.tier as "cohort_floor" | "cohort_typical" | "cohort_ceiling"];
    const targetNightlyRub = positionTarget ?? current.hotel.price.amount / nights;
    const alternatives = hotels.data.filter((hotel) => hotel.hotelId !== current.hotel.hotelId);
    const cheaperRequested = change.hotelPreference === "cheaper";
    const replacement = (cheaperRequested
      ? alternatives
          .filter((hotel) => hotel.priceRub < current.hotel.price.amount)
          .sort((left, right) =>
            left.priceRub - right.priceRub ||
            (right.rating ?? 0) - (left.rating ?? 0))
      : alternatives.filter((hotel) => {
        const nightlyPrice = hotel.priceRub / nights;
        return nightlyPrice >= range.minRub && nightlyPrice <= range.maxRub;
      })
      .sort((left, right) =>
        Math.abs(left.priceRub / nights - targetNightlyRub) -
          Math.abs(right.priceRub / nights - targetNightlyRub) ||
        (right.rating ?? 0) - (left.rating ?? 0),
      ))[0];
    if (!replacement) {
      if (cheaperRequested) {
        throw new Error("Более дешёвого отеля среди доступных вариантов на эти даты не найдено");
      }
      throw new Error("Другого отеля в ценовом диапазоне вашей когорты на эти даты не найдено");
    }
    const hotelAnchor: NearbyAnchor = {
      id: replacement.hotelId,
      type: "hotel",
      name: replacement.name,
      ...(replacement.address ? { address: replacement.address } : {}),
      ...(replacement.latitude !== undefined ? { latitude: replacement.latitude } : {}),
      ...(replacement.longitude !== undefined ? { longitude: replacement.longitude } : {}),
    };
    const nearby = await this.#safeNearby(current.destination, hotelAnchor, {
      includePointsOfInterest: true,
      placeKinds: nearbyPlaceKinds(brief),
    });
    const hotelStatus: SourceStatus = {
      component: "hotel",
      availability: "available",
      required: true,
      source: hotels.source,
      checkedAt: hotels.checkedAt,
    };
    const hotelPoint: MapPoint = {
      id: `hotel-${replacement.hotelId}`,
      type: "hotel",
      name: replacement.name,
      latitude: replacement.latitude ?? current.destination.latitude,
      longitude: replacement.longitude ?? current.destination.longitude,
      ...(replacement.address ? { subtitle: replacement.address } : {}),
      ...(replacement.image ? { image: replacement.image } : {}),
    };
    const hotel: HotelOption = {
      hotelId: replacement.hotelId,
      name: replacement.name,
      stars: replacement.stars,
      ...(replacement.address ? { address: replacement.address } : {}),
      ...(replacement.rating !== undefined ? { rating: replacement.rating } : {}),
      ...(replacement.meal ? { meal: replacement.meal } : {}),
      ...(replacement.image ? { image: replacement.image } : {}),
      price: priceOf(replacement),
      mapPoint: hotelPoint,
      availability: hotelStatus,
    };
    const hotelGroup = this.#restaurantGroup(
      {
        id: `restaurants-hotel-${replacement.hotelId}`,
        anchor: hotelAnchor,
        anchorName: replacement.name,
        anchorMapPointId: hotelPoint.id,
      },
      nearby,
      profile,
      brief,
    );
    const restaurantGroups = [
      hotelGroup,
      ...current.restaurantGroups.filter((group) => group.anchorType === "event"),
    ];
    const points = nearby.data
      .filter((place) => place.type === "poi")
      .slice(0, 6)
      .map((place) => this.#placePoint(place, `${place.distanceMeters} м от отеля`));
    const sources = this.#replaceSources(current.sources, [
      hotelStatus,
      this.#nearbyStatus(restaurantGroups, points.length > 0),
    ]);
    const priceBreakdown = current.priceBreakdown.map((item) =>
      /ноч/u.test(item.label) ? { ...item, price: hotel.price } : item,
    );
    const proposal = this.#withTotals({
      ...current,
      hotel,
      restaurantGroups,
      mapPoints: this.#uniqueMapPoints([
        hotelPoint,
        ...restaurantGroups.flatMap((group) => group.restaurants.map((restaurant) => restaurant.mapPoint)),
        ...points,
        ...current.events.flatMap((event) => event.mapPoint ? [event.mapPoint] : []),
      ]),
      itinerary: this.#program(current, hotelPoint, points, current.events, brief.preferences?.pace?.value),
      sources,
      completeness: this.#completeness(sources),
      warnings: unique([...hotels.warnings, ...nearby.warnings]),
      generatedAt: new Date().toISOString(),
      priceBreakdown,
    });
    return {
      proposal,
      warnings: proposal.warnings,
      changeSummary: [
        `Отель: ${current.hotel.name} → ${hotel.name}`,
        ...(cheaperRequested
          ? [`Стоимость отеля: ${current.hotel.price.amount.toLocaleString("ru-RU")} ₽ → ${hotel.price.amount.toLocaleString("ru-RU")} ₽`]
          : []),
        "Заново подобраны рестораны и места рядом; пересчитана стоимость поездки",
      ],
    };
  }

  async #replaceFlights(
    current: TripProposal,
    brief: TripBrief,
    change: TripChangeSet,
  ): Promise<{ proposal: TripProposal; warnings: string[]; changeSummary: string[] }> {
    const origin = findCity(brief.originCityId);
    if (!origin) throw new Error("Город отправления не поддерживается");
    const direction = change.flightDirection ?? "both";
    const [outboundResult, returnResult] = await Promise.all([
      direction === "return"
        ? Promise.resolve(undefined)
        : this.#provider.flights(origin, current.destination, current.startDate, brief.travelers),
      direction === "outbound"
        ? Promise.resolve(undefined)
        : this.#provider.flights(current.destination, origin, current.endDate, brief.travelers),
    ]);
    const choose = (
      items: FlightInventoryItem[],
      currentFlight: FlightOption,
    ): FlightInventoryItem | undefined => {
      const alternatives = items.filter((item) => !sameFlight(item, currentFlight));
      const preference = change.flightPreference;
      if (!preference) return alternatives[0];
      const currentMetric = flightTimeMetric(currentFlight, preference);
      const earlier = preference === "earlier_departure" || preference === "earlier_arrival";
      return alternatives
        .map((item) => ({ item, metric: flightTimeMetric(item, preference) }))
        .filter((entry): entry is { item: FlightInventoryItem; metric: number } =>
          entry.metric !== undefined &&
          (currentMetric === undefined || (earlier ? entry.metric < currentMetric : entry.metric > currentMetric)),
        )
        .sort((left, right) => earlier ? left.metric - right.metric : right.metric - left.metric)[0]
        ?.item;
    };
    const outbound = outboundResult
      ? choose(outboundResult.data, current.flights.outbound)
      : undefined;
    const returning = returnResult
      ? choose(returnResult.data, current.flights.return)
      : undefined;
    if (!outbound && !returning) {
      const preferenceLabel = {
        earlier_departure: "с более ранним вылетом",
        later_departure: "с более поздним вылетом",
        earlier_arrival: "с более ранним прилётом",
        later_arrival: "с более поздним прилётом",
      }[change.flightPreference ?? "earlier_departure"];
      throw new Error(
        change.flightPreference
          ? `Других доступных рейсов ${preferenceLabel} на эти даты не найдено`
          : "Других доступных рейсов на эти даты не найдено",
      );
    }
    const refreshedResults = [outboundResult, returnResult].filter(
      (result): result is ProviderResult<FlightInventoryItem[]> => Boolean(result),
    );
    const flightStatus: SourceStatus = {
      component: "flights",
      availability: "available",
      required: true,
      source: unique(refreshedResults.map((result) => result.source)).join(" + "),
      checkedAt: refreshedResults.map((result) => result.checkedAt).sort().at(-1)!,
    };
    const flight = (
      item: FlightInventoryItem,
      direction: FlightOption["direction"],
      fromCode: string,
      toCode: string,
      date: string,
    ): FlightOption => ({
      ...(item.offerId ? { offerId: item.offerId } : {}),
      direction,
      fromCode,
      toCode,
      date,
      summary: item.summary,
      ...(item.departureTime ? { departureTime: item.departureTime } : {}),
      ...(item.arrivalTime ? { arrivalTime: item.arrivalTime } : {}),
      price: priceOf(item),
      availability: flightStatus,
    });
    const flights = {
      outbound: outbound
        ? flight(outbound, "outbound", origin.iata, current.destination.iata, current.startDate)
        : current.flights.outbound,
      return: returning
        ? flight(returning, "return", current.destination.iata, origin.iata, current.endDate)
        : current.flights.return,
    };
    const priceBreakdown = current.priceBreakdown.map((item) => {
      if (item.label === "Перелёт туда") return { ...item, price: flights.outbound.price };
      if (item.label === "Перелёт обратно") return { ...item, price: flights.return.price };
      return item;
    });
    const sources = this.#replaceSources(current.sources, [flightStatus]);
    const proposal = this.#withTotals({
      ...current,
      flights,
      sources,
      completeness: this.#completeness(sources),
      warnings: unique(refreshedResults.flatMap((result) => result.warnings)),
      generatedAt: new Date().toISOString(),
      priceBreakdown,
    });
    const timingKey = change.flightPreference?.includes("arrival") ? "arrivalTime" : "departureTime";
    const timingLabel = timingKey === "arrivalTime" ? "прилёт" : "вылет";
    const timingChanges = [
      ...(outbound
        ? [`Рейс туда: ${timingLabel} ${current.flights.outbound[timingKey] ?? "?"} → ${flights.outbound[timingKey] ?? "?"}`]
        : []),
      ...(returning
        ? [`Обратный рейс: ${timingLabel} ${current.flights.return[timingKey] ?? "?"} → ${flights.return[timingKey] ?? "?"}`]
        : []),
    ];
    return {
      proposal,
      warnings: proposal.warnings,
      changeSummary: [
        ...(change.flightPreference ? timingChanges : ["Перепроверены и заменены доступные рейсы"]),
        "Пересчитана полная стоимость",
      ],
    };
  }

  async #refreshNearby(
    current: TripProposal,
    brief: TripBrief,
    profile: PreferenceProfile,
  ): Promise<{ proposal: TripProposal; warnings: string[]; changeSummary: string[] }> {
    const searches: Array<{
      id: string;
      anchor: NearbyAnchor;
      anchorName: string;
      anchorMapPointId?: string;
      includePointsOfInterest: boolean;
      placeKinds?: Array<"culture" | "nature" | "nightlife">;
    }> = [{
      id: `restaurants-hotel-${current.hotel.hotelId}`,
      anchor: {
        id: current.hotel.hotelId,
        type: "hotel",
        name: current.hotel.name,
        ...(current.hotel.address ? { address: current.hotel.address } : {}),
        latitude: current.hotel.mapPoint.latitude,
        longitude: current.hotel.mapPoint.longitude,
      },
      anchorName: current.hotel.name,
      anchorMapPointId: current.hotel.mapPoint.id,
      includePointsOfInterest: true,
      placeKinds: nearbyPlaceKinds(brief),
    }, ...current.events.map((event) => ({
      id: `restaurants-event-${event.eventId}`,
      anchor: this.#eventAnchor(event),
      anchorName: event.name,
      ...(event.mapPoint ? { anchorMapPointId: event.mapPoint.id } : {}),
      includePointsOfInterest: false,
    }))];
    const results = await Promise.all(searches.map(async (search) => ({
      search,
      result: await this.#safeNearby(current.destination, search.anchor, {
        includePointsOfInterest: search.includePointsOfInterest,
        ...(search.placeKinds ? { placeKinds: search.placeKinds } : {}),
      }),
    })));
    const restaurantGroups = results.map(({ search, result }) => {
      const previous = current.restaurantGroups.find((group) =>
        group.anchorType === search.anchor.type && group.anchorId === search.anchor.id,
      );
      return this.#restaurantGroup(
        search,
        result,
        profile,
        brief,
        new Set(previous?.restaurants.map((restaurant) => restaurant.osmId) ?? []),
      );
    });
    const hotelResult = results[0]?.result;
    const points = (hotelResult?.data ?? [])
      .filter((place) => place.type === "poi")
      .slice(0, 6)
      .map((place) => this.#placePoint(place, `${place.distanceMeters} м от отеля`));
    const nearbyStatus = this.#nearbyStatus(restaurantGroups, points.length > 0);
    const sources = this.#replaceSources(current.sources, [nearbyStatus]);
    const proposal: TripProposal = {
      ...current,
      restaurantGroups,
      mapPoints: this.#uniqueMapPoints([
        current.hotel.mapPoint,
        ...restaurantGroups.flatMap((group) => group.restaurants.map((restaurant) => restaurant.mapPoint)),
        ...points,
        ...current.events.flatMap((event) => event.mapPoint ? [event.mapPoint] : []),
      ]),
      itinerary: this.#program(
        current,
        current.hotel.mapPoint,
        points,
        current.events,
        brief.preferences?.pace?.value,
      ),
      sources,
      completeness: this.#completeness(sources),
      warnings: unique(results.flatMap(({ result }) => result.warnings)),
      generatedAt: new Date().toISOString(),
    };
    return {
      proposal,
      warnings: proposal.warnings,
      changeSummary: ["Подобраны другие рестораны рядом с отелем и событиями"],
    };
  }

  async #replaceEvent(
    current: TripProposal,
    brief: TripBrief,
    profile: PreferenceProfile,
    change: TripChangeSet,
  ): Promise<{ proposal: TripProposal; warnings: string[]; changeSummary: string[] }> {
    const result = await this.#provider.events(
      current.destination,
      { startDate: current.startDate, endDate: current.endDate },
      eventSearchInterests(brief, profile),
    );
    const eventStatus: SourceStatus = {
      component: "event",
      availability: "available",
      required: false,
      source: result.source,
      checkedAt: result.checkedAt,
    };
    const currentIds = new Set(current.events.map((event) => event.eventId));
    let events: EventOption[];
    let replacedName: string | undefined;
    if (change.eventName) {
      const target = current.events.find((event) => this.#eventNameMatches(event.name, change.eventName!));
      if (!target) throw new Error(`Событие «${change.eventName}» не найдено в поездке`);
      const retained = current.events.filter((event) => event.eventId !== target.eventId);
      const occupiedDays = new Set(retained.map((event) => event.dateTime?.slice(0, 10)).filter(Boolean));
      const replacement = selectTripEvents(
        result.data.filter((event) =>
          !currentIds.has(event.eventId) &&
          !occupiedDays.has(event.dateTime?.slice(0, 10)) &&
          (!change.eventDate || event.dateTime?.slice(0, 10) === change.eventDate),
        ),
        brief,
        profile,
        { startDate: current.startDate, endDate: current.endDate },
      )[0];
      if (!replacement && change.eventDate) {
        return this.#updateEvents(current, brief, profile, retained, {
          eventStatus,
          warnings: [
            ...result.warnings,
            `Другого подтверждённого события на ${change.eventDate} не найдено; «${target.name}» удалено из программы.`,
          ],
          changeSummary: [
            `Событие «${target.name}» удалено`,
            `Другого события на ${change.eventDate} не найдено`,
            "Обновлены программа, рестораны рядом и стоимость",
          ],
        });
      }
      if (!replacement) throw new Error("Другого подтверждённого события в свободный день не найдено");
      events = [...retained, this.#eventOption(replacement, this.#travelerCount(brief))];
      replacedName = target.name;
    } else {
      const selectedInventory = selectTripEvents(
        result.data,
        brief,
        profile,
        { startDate: current.startDate, endDate: current.endDate },
        currentIds,
      );
      if (selectedInventory.length === 0) {
        throw new Error("Других подтверждённых событий на эти даты не найдено");
      }
      events = selectedInventory.map((event) => this.#eventOption(event, this.#travelerCount(brief)));
    }
    return this.#updateEvents(current, brief, profile, events, {
      eventStatus,
      warnings: result.warnings,
      warnBelowTarget: true,
      changeSummary: [
        replacedName
          ? `Событие «${replacedName}» заменено`
          : "Подобран другой набор событий",
        "Обновлены программа, рестораны рядом и стоимость",
      ],
    });
  }

  async #addEvent(
    current: TripProposal,
    brief: TripBrief,
    profile: PreferenceProfile,
    change: TripChangeSet,
  ): Promise<{ proposal: TripProposal; warnings: string[]; changeSummary: string[] }> {
    this.#assertEventDate(change.eventDate, current);
    const result = await this.#provider.events(
      current.destination,
      { startDate: current.startDate, endDate: current.endDate },
      eventSearchInterests(brief, profile),
    );
    const currentIds = new Set(current.events.map((event) => event.eventId));
    let candidates = result.data.filter((event) =>
      !currentIds.has(event.eventId) &&
      (!change.eventDate || event.dateTime?.slice(0, 10) === change.eventDate),
    );
    if (change.eventName) {
      candidates = candidates.filter((event) => this.#eventNameMatches(event.name, change.eventName!));
    }
    const selected = change.eventName
      ? candidates.sort((left, right) =>
          Number(normalizeSignal(right.name) === normalizeSignal(change.eventName!)) -
          Number(normalizeSignal(left.name) === normalizeSignal(change.eventName!)) ||
          String(left.dateTime ?? "").localeCompare(String(right.dateTime ?? "")),
        )[0]
      : selectTripEvents(
          candidates,
          brief,
          profile,
          { startDate: current.startDate, endDate: current.endDate },
        )[0];
    if (!selected) {
      const details = [
        change.eventName ? `с названием «${change.eventName}»` : "",
        change.eventDate ? `на ${change.eventDate}` : "",
      ].filter(Boolean).join(" ");
      throw new Error(`Подтверждённое событие ${details || "по этим условиям"} не найдено`);
    }
    const event = this.#eventOption(selected, this.#travelerCount(brief));
    const eventStatus: SourceStatus = {
      component: "event",
      availability: "available",
      required: false,
      source: result.source,
      checkedAt: result.checkedAt,
    };
    return this.#updateEvents(current, brief, profile, [...current.events, event], {
      eventStatus,
      warnings: result.warnings,
      changeSummary: [
        `Добавлено событие «${event.name}»${event.dateTime ? ` на ${event.dateTime.slice(0, 10)}` : ""}`,
        "Обновлены программа, рестораны рядом и стоимость",
      ],
    });
  }

  async #removeEvent(
    current: TripProposal,
    brief: TripBrief,
    profile: PreferenceProfile,
    change: TripChangeSet,
  ): Promise<{ proposal: TripProposal; warnings: string[]; changeSummary: string[] }> {
    this.#assertEventDate(change.eventDate, current);
    if (!change.eventName && !change.eventDate) {
      throw new Error("Укажите название события или дату, с которой его нужно убрать");
    }
    const removed = current.events.filter((event) =>
      (!change.eventName || this.#eventNameMatches(event.name, change.eventName)) &&
      (!change.eventDate || event.dateTime?.slice(0, 10) === change.eventDate),
    );
    if (removed.length === 0) {
      const details = [
        change.eventName ? `«${change.eventName}»` : "",
        change.eventDate ? `на ${change.eventDate}` : "",
      ].filter(Boolean).join(" ");
      throw new Error(`Событие ${details} не найдено в поездке`);
    }
    const removedIds = new Set(removed.map((event) => event.eventId));
    const events = current.events.filter((event) => !removedIds.has(event.eventId));
    const summary = removed.length === 1
      ? `Удалено событие «${removed[0]!.name}»`
      : `Удалены события на ${change.eventDate}`;
    return this.#updateEvents(current, brief, profile, events, {
      warnings: current.warnings.filter((warning) => !warning.startsWith("Целевое количество событий:")),
      changeSummary: [summary, "Обновлены программа, рестораны рядом и стоимость"],
    });
  }

  async #updateEvents(
    current: TripProposal,
    brief: TripBrief,
    profile: PreferenceProfile,
    nextEvents: EventOption[],
    options: {
      eventStatus?: SourceStatus;
      warnings: string[];
      changeSummary: string[];
      warnBelowTarget?: boolean;
    },
  ): Promise<{ proposal: TripProposal; warnings: string[]; changeSummary: string[] }> {
    const events = [...nextEvents].sort((left, right) =>
      String(left.dateTime ?? "").localeCompare(String(right.dateTime ?? "")),
    );
    const withoutEvent = current.priceBreakdown.filter((item) => !item.label.startsWith("Событие:"));
    const insertion = withoutEvent.findIndex((item) => item.label === "Еда");
    const eventPrices = events.flatMap((event) =>
      event.price ? [{ label: `Событие: ${event.name}`, price: event.price }] : [],
    );
    withoutEvent.splice(insertion < 0 ? withoutEvent.length : insertion, 0, ...eventPrices);
    const currentIds = new Set(current.events.map((event) => event.eventId));
    const newEvents = events.filter((event) => !currentIds.has(event.eventId));
    const newGroupsWithResults = await Promise.all(newEvents.map(async (event) => {
      const anchor = this.#eventAnchor(event);
      const nearby = await this.#safeNearby(current.destination, anchor);
      return {
        group: this.#restaurantGroup(
          {
            id: `restaurants-event-${event.eventId}`,
            anchor,
            anchorName: event.name,
            ...(event.mapPoint ? { anchorMapPointId: event.mapPoint.id } : {}),
          },
          nearby,
          profile,
          brief,
        ),
        warnings: nearby.warnings,
      };
    }));
    const nextEventIds = new Set(events.map((event) => event.eventId));
    const groupCandidates = [
      ...current.restaurantGroups.filter((group) =>
        group.anchorType === "hotel" || nextEventIds.has(group.anchorId),
      ),
      ...newGroupsWithResults.map(({ group }) => group),
    ].filter((group, index, groups) => groups.findIndex((candidate) => candidate.id === group.id) === index);
    const restaurantGroups = [
      ...groupCandidates.filter((group) => group.anchorType === "hotel"),
      ...events.flatMap((event) => {
        const group = groupCandidates.find((candidate) =>
          candidate.anchorType === "event" && candidate.anchorId === event.eventId,
        );
        return group ? [group] : [];
      }),
    ];
    const points = current.mapPoints.filter((point) => point.type === "poi");
    const replacements = [
      ...(options.eventStatus ? [options.eventStatus] : []),
      this.#nearbyStatus(restaurantGroups, points.length > 0),
    ];
    const sources = this.#replaceSources(current.sources, replacements);
    const proposal = this.#withTotals({
      ...current,
      events,
      restaurantGroups,
      mapPoints: this.#uniqueMapPoints([
        current.hotel.mapPoint,
        ...restaurantGroups.flatMap((group) => group.restaurants.map((restaurant) => restaurant.mapPoint)),
        ...points,
        ...events.flatMap((event) => event.mapPoint ? [event.mapPoint] : []),
      ]),
      itinerary: this.#program(
        current,
        current.hotel.mapPoint,
        points,
        events,
        brief.preferences?.pace?.value,
      ),
      sources,
      completeness: this.#completeness(sources),
      warnings: unique([
        ...options.warnings,
        ...newGroupsWithResults.flatMap(({ warnings }) => warnings),
        ...(options.warnBelowTarget && events.length < targetEventCount(
          current.startDate,
          current.endDate,
          brief.preferences?.pace?.value,
        )
          ? [`Целевое количество событий: ${targetEventCount(current.startDate, current.endDate, brief.preferences?.pace?.value)}; в разные дни найдено: ${events.length}.`]
          : []),
      ]),
      generatedAt: new Date().toISOString(),
      priceBreakdown: withoutEvent,
    });
    return {
      proposal,
      warnings: proposal.warnings,
      changeSummary: options.changeSummary,
    };
  }

  #assertEventDate(date: string | undefined, current: TripProposal): void {
    if (date && (date < current.startDate || date > current.endDate)) {
      throw new Error(`Дата ${date} находится за пределами поездки`);
    }
  }

  #eventNameMatches(value: string, target: string): boolean {
    const normalizedValue = normalizeSignal(value);
    const normalizedTarget = normalizeSignal(target);
    return normalizedValue === normalizedTarget ||
      normalizedValue.includes(normalizedTarget) ||
      normalizedTarget.includes(normalizedValue);
  }

  #travelerCount(brief: TripBrief): number {
    return brief.travelers.adults + brief.travelers.childrenAges.length;
  }

  async #safeNearby(
    city: TripProposal["destination"],
    anchor: NearbyAnchor,
    options?: NearbySearchOptions,
  ): Promise<ProviderResult<NearbyPlace[]>> {
    try {
      return await this.#provider.nearby(city, anchor, options);
    } catch (error) {
      return {
        data: [],
        warnings: [`Места рядом с «${anchor.name}» недоступны: ${message(error)}`],
        isFallback: false,
        source: "OpenStreetMap",
        checkedAt: new Date().toISOString(),
      };
    }
  }

  #placePoint(place: NearbyPlace, subtitle?: string): MapPoint {
    return {
      id: `osm-${place.osmId.replaceAll("/", "-")}`,
      type: place.type,
      name: place.name,
      latitude: place.latitude,
      longitude: place.longitude,
      ...(subtitle ? { subtitle } : {}),
      ...(place.image ? { image: place.image } : {}),
    };
  }

  #restaurantGroup(
    search: {
      id: string;
      anchor: NearbyAnchor;
      anchorName: string;
      anchorMapPointId?: string;
    },
    result: ProviderResult<NearbyPlace[]>,
    profile: PreferenceProfile,
    brief: TripBrief,
    excludedIds: Set<string> = new Set(),
  ): RestaurantGroup {
    const interests = (brief.interests ?? []).map(normalizeSignal).filter(Boolean);
    const favorites = profile.favoriteDiningMerchants.map(normalizeSignal).filter(Boolean);
    const preferredCuisines = profile.diningProfile.preferredCuisines.map(normalizeSignal).filter(Boolean);
    const availability: SourceStatus = {
      component: "nearby",
      availability: "unavailable",
      required: false,
      source: result.source,
      checkedAt: result.checkedAt,
    };
    const candidates = result.data.filter((place) => place.type === "restaurant");
    const freshCandidates = candidates.some((place) => !excludedIds.has(place.osmId))
      ? candidates.filter((place) => !excludedIds.has(place.osmId))
      : candidates;
    const restaurants: Restaurant[] = freshCandidates
        .map((place, index) => {
          const name = normalizeSignal(place.name);
          const cuisine = normalizeSignal(place.cuisine ?? "");
          const favorite = favorites.some((merchant) =>
            merchant.length >= 4 && name.length >= 4 &&
            (merchant === name || merchant.includes(name) || name.includes(merchant)),
          );
          const explicitCuisineMatch = Boolean(cuisine) && interests.some((interest) =>
            cuisine.includes(interest) || interest.includes(cuisine),
          );
          const profileCuisineMatch = Boolean(cuisine) && preferredCuisines.some((interest) =>
            cuisine.includes(interest) || interest.includes(cuisine),
          );
          return {
            place,
            index,
            score: (favorite ? 10_000 : 0) + (explicitCuisineMatch ? 1_000 : 0) +
              (profileCuisineMatch ? 750 : 0) - place.distanceMeters,
            matchReasons: [
              ...(favorite ? ["Вы часто выбираете это заведение или сеть."] : []),
              ...(explicitCuisineMatch ? [`Совпадает с интересом «${place.cuisine}».`] : []),
              ...(profileCuisineMatch && !explicitCuisineMatch
                ? [`Кухня совпадает с вашим банковским профилем: ${place.cuisine}.`]
                : []),
              `${place.distanceMeters} м от «${search.anchorName}».`,
            ],
          };
        })
        .sort((left, right) => right.score - left.score || left.index - right.index)
        .slice(0, 3)
        .map(({ place, matchReasons }) => ({
          osmId: place.osmId,
          name: place.name,
          ...(place.cuisine ? { cuisine: place.cuisine } : {}),
          ...(place.openingHours ? { openingHours: place.openingHours } : {}),
          ...(place.address ? { address: place.address } : {}),
          ...(place.rating !== undefined ? { rating: place.rating } : {}),
          ...(place.reviewCount !== undefined ? { reviewCount: place.reviewCount } : {}),
          ...(place.averageCheck ? { averageCheck: place.averageCheck } : {}),
          ...(place.attributes?.length ? { attributes: place.attributes } : {}),
          ...(place.delivery !== undefined ? { delivery: place.delivery } : {}),
          ...(place.sourceUrl ? { sourceUrl: place.sourceUrl } : {}),
          distanceMeters: place.distanceMeters,
          matchReasons,
          mapPoint: this.#placePoint(place, place.cuisine ? `Кухня: ${place.cuisine}` : "Ресторан"),
          availability: { ...availability, availability: "available" as const },
        }));
    return {
      id: search.id,
      anchorType: search.anchor.type,
      anchorId: search.anchor.id,
      anchorName: search.anchorName,
      ...(search.anchorMapPointId ? { anchorMapPointId: search.anchorMapPointId } : {}),
      availability: restaurants.length > 0
        ? { ...availability, availability: "available" }
        : { ...availability, message: `Рестораны рядом с «${search.anchorName}» не найдены` },
      restaurants,
    };
  }

  #eventAnchor(event: EventOption): NearbyAnchor {
    return {
      id: event.eventId,
      type: "event",
      name: event.venue ?? event.name,
      ...(event.address ? { address: event.address } : {}),
      ...(event.mapPoint
        ? { latitude: event.mapPoint.latitude, longitude: event.mapPoint.longitude }
        : {}),
    };
  }

  #nearbyStatus(groups: RestaurantGroup[], hasPoints = false): SourceStatus {
    const available = hasPoints || groups.some((group) => group.restaurants.length > 0);
    return {
      component: "nearby",
      availability: available ? "available" : "unavailable",
      required: false,
      source: unique(groups.map((group) => group.availability.source)).join(" + ") || "OpenStreetMap",
      checkedAt: groups.map((group) => group.availability.checkedAt).sort().at(-1) ?? new Date().toISOString(),
      ...(!available ? { message: "Рестораны и достопримечательности рядом не найдены" } : {}),
    };
  }

  #uniqueMapPoints(points: MapPoint[]): MapPoint[] {
    return [...new Map(points.map((point) => [point.id, point])).values()];
  }

  #eventOption(item: EventInventoryItem, people: number): EventOption {
    const availability: SourceStatus = {
      component: "event",
      availability: "available",
      required: false,
      source: item.source,
      checkedAt: item.checkedAt,
    };
    const mapPoint =
      item.latitude !== undefined && item.longitude !== undefined
        ? {
            id: `event-${item.eventId}`,
            type: "event" as const,
            name: item.name,
            latitude: item.latitude,
            longitude: item.longitude,
            ...(item.venue ? { subtitle: item.venue } : {}),
            ...(item.image ? { image: item.image } : {}),
          }
        : undefined;
    return {
      eventId: item.eventId,
      name: item.name,
      kind: item.kind,
      ...(item.genres?.length ? { genres: item.genres } : {}),
      ...(item.ageRestriction ? { ageRestriction: item.ageRestriction } : {}),
      ...(item.rating !== undefined ? { rating: item.rating } : {}),
      ...(item.dateTime ? { dateTime: item.dateTime } : {}),
      ...(item.venue ? { venue: item.venue } : {}),
      ...(item.address ? { address: item.address } : {}),
      ...(item.image ? { image: item.image } : {}),
      ...(item.priceRub
        ? {
            price: {
              amount: item.priceRub * people,
              currency: "RUB" as const,
              kind: "live" as const,
              source: item.source,
              checkedAt: item.checkedAt,
              expiresAt: new Date(Date.parse(item.checkedAt) + 15 * 60_000).toISOString(),
            },
          }
        : {}),
      ...(mapPoint ? { mapPoint } : {}),
      availability,
    };
  }

  #replaceSources(current: SourceStatus[], replacements: SourceStatus[]): SourceStatus[] {
    const components = new Set(replacements.map((item) => item.component));
    return [...current.filter((item) => !components.has(item.component)), ...replacements];
  }

  #completeness(sources: SourceStatus[]): TripProposal["completeness"] {
    return sources.some((source) => source.availability === "unavailable") ? "partial" : "complete";
  }

  #withTotals(proposal: TripProposal): TripProposal {
    const liveSubtotalRub = proposal.priceBreakdown
      .filter((item) => item.price.kind === "live")
      .reduce((sum, item) => sum + item.price.amount, 0);
    const estimatedSubtotalRub = proposal.priceBreakdown
      .filter((item) => item.price.kind === "estimated")
      .reduce((sum, item) => sum + item.price.amount, 0);
    const checkedAt = new Date().toISOString();
    return {
      ...proposal,
      liveSubtotalRub,
      estimatedSubtotalRub,
      totalPrice: {
        amount: liveSubtotalRub + estimatedSubtotalRub,
        currency: "RUB",
        kind: estimatedSubtotalRub > 0 ? "estimated" : "live",
        source: "Сводный расчёт Travel Nova",
        checkedAt,
      },
    };
  }

  #program(
    current: TripProposal,
    hotel: MapPoint,
    points: MapPoint[],
    events: EventOption[],
    pace: TripPace = "balanced",
  ): TripProposal["itinerary"] {
    const nights = Math.max(
      1,
      Math.round((Date.parse(current.endDate) - Date.parse(current.startDate)) / 86_400_000),
    );
    const itinerary: TripProposal["itinerary"] = [
      {
        id: randomUUID(),
        day: 1,
        time: "После прилёта",
        title: "Заселиться и почувствовать район",
        description: `Спокойный старт рядом с ${hotel.name}.`,
        mapPointId: hotel.id,
      },
    ];
    const pointLimit = pace === "relaxed" ? 1 : pace === "active" ? 3 : 2;
    for (const [index, point] of points.slice(0, pointLimit).entries()) {
      itinerary.push({
        id: randomUUID(),
        day: Math.min(index + 2, nights + 1),
        time: "11:00",
        title: point.name,
        description: point.subtitle ?? "Точка дневной прогулки.",
        mapPointId: point.id,
      });
    }
    for (const event of events) {
      const eventDay = event.dateTime
        ? Math.max(1, Math.min(nights + 1, Math.floor((Date.parse(event.dateTime) - Date.parse(current.startDate)) / 86_400_000) + 1))
        : Math.min(2, nights + 1);
      itinerary.push({
        id: randomUUID(),
        day: eventDay,
        time: event.dateTime?.slice(11, 16) || "19:00",
        title: event.name,
        description: event.venue ? `Подтверждённая площадка: ${event.venue}.` : "Событие из афиши.",
        ...(event.mapPoint ? { mapPointId: event.mapPoint.id } : {}),
      });
    }
    itinerary.push({
      id: randomUUID(),
      day: nights + 1,
      time: "Перед вылетом",
      title: "Последняя прогулка и дорога в аэропорт",
      description: "Оставляем запас времени и не перегружаем финальный день.",
    });
    const timeOrder = (value: string) => {
      const match = value.match(/^(\d{2}):(\d{2})$/u);
      if (match) return Number(match[1]) * 60 + Number(match[2]);
      return value === "После прилёта" ? 0 : 24 * 60;
    };
    return itinerary.sort((left, right) =>
      left.day - right.day || timeOrder(left.time) - timeOrder(right.time),
    );
  }

  #fullChangeSummary(change: TripChangeSet): string[] {
    const labels: Record<TripChangeSet["action"], string> = {
      cheaper: "Поездка полностью пересобрана в более экономном варианте",
      more_comfort: "Поездка полностью пересобрана с приоритетом комфорта",
      replace_hotel: "Заменён отель",
      replace_flight: "Заменён перелёт",
      replace_event: "Обновлены события",
      add_event: "Добавлено событие",
      remove_event: "Удалено событие",
      more_restaurants: "Обновлены рестораны",
      change_destination: "Изменён город и полностью пересобрана поездка",
      change_dates: "Изменены даты и полностью пересобрана поездка",
      change_budget: "Изменён бюджет и полностью пересобрана поездка",
      general: "Поездка полностью пересобрана по пожеланию",
    };
    return [labels[change.action]];
  }

  #applyChange(brief: TripBrief, current: TripProposal, change: TripChangeSet): TripBrief {
    let next: TripBrief = {
      ...brief,
      destinationCityId: current.destination.id,
      time: { mode: "exact", startDate: current.startDate, endDate: current.endDate },
    };
    if (change.destinationName) {
      const destination = findCityByName(change.destinationName);
      if (!destination) throw new Error(`Город «${change.destinationName}» пока не поддерживается`);
      next = { ...next, destinationCityId: destination.id };
    }
    if (change.startDate && change.endDate) {
      if (change.endDate <= change.startDate) throw new Error("Дата возвращения должна быть позже выезда");
      next = { ...next, time: { mode: "exact", startDate: change.startDate, endDate: change.endDate } };
    }
    if (change.budgetRub) next = { ...next, budgetRub: change.budgetRub };
    if (change.action === "cheaper" && !change.budgetRub) {
      next = { ...next, budgetRub: Math.max(10_000, Math.floor(current.totalPrice.amount * 0.85)) };
    }
    if (change.action === "more_comfort") {
      const { budgetRub: _budget, ...withoutBudget } = next;
      next = withoutBudget;
    }
    return next;
  }

  #chatResponse(
    change: TripChangeSet,
    proposal: TripProposal,
    warnings: string[],
    changeSummary: string[],
  ): string {
    const actions: Record<TripChangeSet["action"], string> = {
      cheaper: "Собрал более экономную версию",
      more_comfort: "Добавил больше комфорта",
      replace_hotel: "Подобрал другой отель",
      replace_flight: "Перепроверил и заменил перелёт",
      replace_event: "Обновил события в программе",
      add_event: "Добавил подтверждённое событие",
      remove_event: "Убрал событие из программы",
      more_restaurants: "Обновил гастрономическую часть",
      change_destination: "Пересобрал поездку в новом городе",
      change_dates: "Пересобрал поездку на новые даты",
      change_budget: "Пересчитал поездку под новый бюджет",
      general: "Учёл пожелание и пересобрал поездку",
    };
    const warning = warnings[0] ? ` Обратите внимание: ${warnings[0]}` : "";
    const changed = changeSummary.length ? ` Изменения: ${changeSummary.join("; ")}.` : "";
    return `${actions[change.action]}. Новый ориентир — ${proposal.totalPrice.amount.toLocaleString("ru-RU")} ₽.${changed}${warning}`;
  }
}
