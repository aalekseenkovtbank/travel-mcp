import { randomUUID } from "node:crypto";

import type {
  City,
  EventOption,
  FlightOption,
  HotelOption,
  IncomeCohort,
  ItineraryItem,
  MapPoint,
  PreferenceProfile,
  Price,
  Restaurant,
  RestaurantGroup,
  SourceStatus,
  TripBrief,
  TripPace,
  TripProposal,
} from "@travel-growth-inspiration/contracts";

import { cities, findCity } from "../catalog/cities.js";
import {
  fallbackTripTitle,
  type EditorialService,
} from "../editorial/editorial-service.js";
import type {
  DateWindow,
  EventInventoryItem,
  FlightInventoryItem,
  HotelInventoryItem,
  NearbyAnchor,
  NearbyPlace,
  PlannerDataProvider,
  ProviderResult,
} from "../providers/provider-types.js";
import {
  UnavailableWeatherService,
  type WeatherLookupResult,
  type WeatherService,
} from "../providers/open-meteo-weather-service.js";

type InventoryBundle = {
  city: City;
  window: DateWindow;
  outbound: FlightInventoryItem[];
  inbound: FlightInventoryItem[];
  hotels: HotelInventoryItem[];
  warnings: string[];
  sources: SourceStatus[];
  textPreferenceScore: number;
  profileScore: number;
  hardViolationCount: number;
  preferenceReasons: string[];
};

type BundleSearchResult = {
  bundles: InventoryBundle[];
  warnings: string[];
};

type BundleSearchOptions = {
  parallelWindows?: boolean;
  onBundle?: (bundle: InventoryBundle) => void;
};

type CandidateSeed = {
  bundle: InventoryBundle;
  outbound: FlightInventoryItem;
  inbound: FlightInventoryItem;
  hotel: HotelInventoryItem;
  projectedTotalRub: number;
};

export type HotelPricePosition = "cohort_floor" | "cohort_typical" | "cohort_ceiling";

export type HotelNightlyPriceRange = {
  minRub: number;
  typicalRub: number;
  maxRub: number;
};

export type CompilerProgress = {
  shortlist?: (cityList: City[]) => void;
  candidate?: (city: City, message: string) => void;
  partial?: (proposal: TripProposal) => void;
};

export type CompileResult = {
  proposals: TripProposal[];
  warnings: string[];
};

type ClimateAssessment = {
  score: number;
  hardViolationCount: number;
  reasons: string[];
  available: boolean;
};

const DAY_MS = 86_400_000;

const HOTEL_NIGHTLY_RANGES: Record<IncomeCohort, HotelNightlyPriceRange> = {
  unknown: { minRub: 3_000, typicalRub: 7_000, maxRub: 14_000 },
  up_to_50k: { minRub: 1_800, typicalRub: 3_200, maxRub: 5_500 },
  "50k_to_100k": { minRub: 2_500, typicalRub: 4_500, maxRub: 8_000 },
  "100k_to_200k": { minRub: 4_000, typicalRub: 7_000, maxRub: 14_000 },
  "200k_to_500k": { minRub: 7_000, typicalRub: 12_000, maxRub: 24_000 },
  "500k_to_1m": { minRub: 12_000, typicalRub: 20_000, maxRub: 40_000 },
  "1m_plus": { minRub: 20_000, typicalRub: 35_000, maxRub: 70_000 },
};

export function hotelNightlyPriceRange(cohort: IncomeCohort): HotelNightlyPriceRange {
  return HOTEL_NIGHTLY_RANGES[cohort];
}

function addDays(date: string, days: number): string {
  const value = new Date(`${date}T12:00:00.000Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

function daysBetween(startDate: string, endDate: string): number {
  return Math.max(1, Math.round((Date.parse(endDate) - Date.parse(startDate)) / DAY_MS));
}

function hotelNightlyPrice(seed: CandidateSeed): number {
  return seed.hotel.priceRub / daysBetween(seed.bundle.window.startDate, seed.bundle.window.endDate);
}

function hotelPreferenceScore(hotel: HotelInventoryItem, profile: PreferenceProfile): number {
  const travel = profile.behavioralInsights?.travel;
  if (!travel) return 0;
  const starScore = travel.preferredHotelStars.reduce((sum, preference) =>
    sum + (Number.parseInt(preference.value, 10) === hotel.stars
      ? Math.min(12, 4 + preference.evidenceCount * 2)
      : 0), 0);
  const meal = normalizeSignal(hotel.meal ?? "");
  const mealScore = travel.preferredMealTypes.reduce((sum, preference) => {
    const signal = normalizeSignal(preference.value);
    return sum + (meal && (meal.includes(signal) || signal.includes(meal))
      ? Math.min(8, 3 + preference.evidenceCount)
      : 0);
  }, 0);
  return starScore + mealScore;
}

function cohortTargets(profile: PreferenceProfile): Array<{
  position: HotelPricePosition;
  amountRub: number;
}> {
  const range = hotelNightlyPriceRange(profile.incomeCohort);
  return [
    { position: "cohort_floor", amountRub: range.minRub },
    { position: "cohort_typical", amountRub: range.typicalRub },
    { position: "cohort_ceiling", amountRub: range.maxRub },
  ];
}

export function targetEventCount(
  startDate: string,
  endDate: string,
  pace: TripPace = "balanced",
): number {
  const divisor = pace === "relaxed" ? 4 : pace === "active" ? 2 : 3;
  return Math.min(6, Math.ceil((daysBetween(startDate, endDate) + 1) / divisor));
}

function unique<T>(values: T[]): T[] {
  return [...new Set(values)];
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

function sourceStatus(
  component: SourceStatus["component"],
  required: boolean,
  result: Pick<ProviderResult<unknown>, "data" | "source" | "checkedAt">,
  emptyMessage: string,
): SourceStatus {
  const unavailable = Array.isArray(result.data) && result.data.length === 0;
  return {
    component,
    availability: unavailable ? "unavailable" : "available",
    required,
    source: result.source,
    checkedAt: result.checkedAt,
    ...(unavailable ? { message: emptyMessage } : {}),
  };
}

function cityPreferenceScores(
  city: City,
  brief: TripBrief,
  profile: PreferenceProfile,
): { text: number; profile: number } {
  const scoreTags = (signals: string[], weight: number) => city.tags.reduce(
    (sum, tag) => sum + signals.filter((signal) => signal.includes(tag) || tag.includes(signal)).length * weight,
    0,
  );
  const textSignals = (brief.interests ?? []).map((value) => value.toLocaleLowerCase("ru"));
  const profileSignals = [
    ...profile.preferredCategories,
    ...profile.eventInterests,
  ].map((value) => value.toLocaleLowerCase("ru"));
  const repeatPenalty = profile.previousDestinations.some((name) =>
    name.toLocaleLowerCase("ru").includes(city.name.toLocaleLowerCase("ru")),
  )
    ? -2
    : 1;
  const presetBonus =
    brief.preset === "event" && city.tags.some((tag) => /концерт|театр/u.test(tag))
      ? 4
      : brief.preset === "weekend" && city.tags.some((tag) => /прогул|гастроном|архитект/u.test(tag))
        ? 2
        : 0;
  const explicitScore = (brief.preferences?.destinationTags ?? []).reduce((sum, preference) => {
    const signal = normalizeSignal(preference.value);
    const matches = city.tags.some((tag) => {
      const normalizedTag = normalizeSignal(tag);
      return signal === normalizedTag || signal.includes(normalizedTag) || normalizedTag.includes(signal);
    });
    if (!matches) return sum;
    const amount = preference.strength === "hard" ? 120 : 36;
    return sum + (preference.polarity === "prefer" ? amount : -amount);
  }, 0);
  return {
    text: explicitScore + scoreTags(textSignals, 12) + presetBonus,
    profile: scoreTags(profileSignals, 4) + repeatPenalty,
  };
}

function hardTagViolations(city: City, brief: TripBrief): number {
  return (brief.preferences?.destinationTags ?? []).filter((preference) => {
    if (preference.strength !== "hard") return false;
    const signal = normalizeSignal(preference.value);
    const matches = city.tags.some((tag) => {
      const normalizedTag = normalizeSignal(tag);
      return signal === normalizedTag || signal.includes(normalizedTag) || normalizedTag.includes(signal);
    });
    return preference.polarity === "prefer" ? !matches : matches;
  }).length;
}

function destinationPreferenceReasons(city: City, brief: TripBrief): string[] {
  return (brief.preferences?.destinationTags ?? [])
    .filter((preference) => preference.polarity === "prefer")
    .filter((preference) => {
      const signal = normalizeSignal(preference.value);
      return city.tags.some((tag) => {
        const normalizedTag = normalizeSignal(tag);
        return signal === normalizedTag || signal.includes(normalizedTag) || normalizedTag.includes(signal);
      });
    })
    .map((preference) => `Совпадает с пожеланием «${preference.value}».`)
    .slice(0, 2);
}

function climateKey(city: City, window: DateWindow): string {
  return `${city.id}:${window.startDate}:${window.endDate}`;
}

function climateAssessment(
  weather: WeatherLookupResult,
  brief: TripBrief,
): ClimateAssessment {
  const preference = brief.preferences?.climate;
  if (!preference) return { score: 0, hardViolationCount: 0, reasons: [], available: true };
  if (!weather.available || weather.data.days.length === 0) {
    return {
      score: -40,
      hardViolationCount: preference.strength === "hard" ? 1 : 0,
      reasons: [],
      available: false,
    };
  }
  const averageMinimum = weather.data.days.reduce((sum, day) => sum + day.temperatureMinC, 0) /
    weather.data.days.length;
  const averageMaximum = weather.data.days.reduce((sum, day) => sum + day.temperatureMaxC, 0) /
    weather.data.days.length;
  const averagePrecipitation = weather.data.days.reduce((sum, day) =>
    sum + (day.kind === "forecast" ? day.precipitationProbabilityPct : day.precipitationFrequencyPct), 0) /
    weather.data.days.length;
  let score = 0;
  let violations = 0;
  const reasons: string[] = [];
  if (preference.maxDayTemperatureC !== undefined) {
    const delta = averageMaximum - preference.maxDayTemperatureC;
    if (delta <= 0) {
      score += 45;
      reasons.push(`Днём около ${Math.round(averageMaximum)} °C — не выше пожелания.`);
    } else {
      score -= delta * 12;
      if (preference.strength === "hard") violations += 1;
    }
  }
  if (preference.minDayTemperatureC !== undefined) {
    const delta = preference.minDayTemperatureC - averageMaximum;
    if (delta <= 0) {
      score += 35;
      reasons.push(`Ожидается около ${Math.round(averageMaximum)} °C днём.`);
    } else {
      score -= delta * 10;
      if (preference.strength === "hard") violations += 1;
    }
  }
  if (preference.precipitation && preference.precipitation !== "any") {
    const matches = preference.precipitation === "low"
      ? averagePrecipitation <= 35
      : averagePrecipitation >= 50;
    if (matches) {
      score += 24;
      reasons.push(
        preference.precipitation === "low" ? "Невысокая вероятность осадков." : "Вероятна дождливая погода.",
      );
    } else {
      score -= 24;
      if (preference.strength === "hard") violations += 1;
    }
  }
  if (preference.minDayTemperatureC !== undefined && averageMinimum >= preference.minDayTemperatureC) {
    score += 5;
  }
  return {
    score,
    hardViolationCount: violations,
    reasons: unique(reasons).slice(0, 2),
    available: true,
  };
}

function dateWindows(brief: TripBrief): DateWindow[] {
  const time = brief.time;
  if (time.mode === "exact") {
    return [{ startDate: time.startDate, endDate: time.endDate }];
  }
  const latestStart = addDays(time.windowEnd, -time.nights);
  if (latestStart < time.windowStart) {
    throw new Error("Гибкий период короче заданной продолжительности поездки");
  }
  const availableDays = Math.max(0, daysBetween(time.windowStart, latestStart));
  const offsets = unique([0, Math.floor(availableDays / 2), availableDays]).slice(0, 3);
  return offsets.map((offset) => {
    const startDate = addDays(time.windowStart, offset);
    return { startDate, endDate: addDays(startDate, time.nights) };
  });
}

function normalizeSignal(value: string): string {
  return value
    .toLocaleLowerCase("ru")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function paceLabel(pace: TripPace): string {
  return pace === "relaxed" ? "спокойный темп" : pace === "active" ? "активный темп" : "сбалансированный темп";
}

function placeCategoryLabel(category: string | undefined): string {
  return {
    museum: "музей",
    gallery: "галерея",
    attraction: "достопримечательность",
    historic: "историческое место",
    viewpoint: "смотровая площадка",
    park: "парк",
    garden: "сад",
    nature_reserve: "природная зона",
    beach: "пляж",
    wood: "природная зона",
    bar: "бар",
    pub: "паб",
    nightclub: "клуб",
    music_venue: "музыкальная площадка",
  }[category ?? ""] ?? "место рядом";
}

export function eventSearchInterests(brief: TripBrief, profile: PreferenceProfile): string[] {
  const insights = profile.behavioralInsights?.events;
  return unique([
    ...(brief.interests ?? []),
    ...profile.eventInterests,
    ...(insights?.kindAffinities.map((item) => item.value) ?? []),
    ...(insights?.genreAffinities.slice(0, 6).map((item) => item.value) ?? []),
  ]);
}

export function nearbyPlaceKinds(brief: TripBrief): Array<"culture" | "nature" | "nightlife"> {
  const signals = [
    ...(brief.interests ?? []),
    ...(brief.preferences?.destinationTags ?? []).map((item) => item.value),
    ...(brief.preferences?.activities ?? []).map((item) => item.value),
  ].map(normalizeSignal);
  const result = new Set<"culture" | "nature" | "nightlife">(["culture"]);
  if (signals.some((signal) => ["природ", "парк", "поход", "горы", "море", "байкал", "прогул"].some((value) => signal.includes(value)))) {
    result.add("nature");
  }
  if (signals.some((signal) => ["бар", "паб", "клуб", "тус", "ночн"].some((value) => signal.includes(value)))) {
    result.add("nightlife");
  }
  return [...result];
}

function eventMinimumAge(value: string | undefined): number | undefined {
  const match = value?.match(/(\d{1,2})\s*\+/u);
  return match ? Number(match[1]) : undefined;
}

function eventDayPart(value: string | undefined): string | undefined {
  const match = value?.match(/T(\d{2}):/u) ?? value?.match(/\b(\d{2}):/u);
  const hour = Number(match?.[1]);
  if (!Number.isInteger(hour)) return undefined;
  if (hour < 6) return "ночь";
  if (hour < 12) return "утро";
  if (hour < 18) return "день";
  return "вечер";
}

function eventWeekday(value: string | undefined): string | undefined {
  if (!value) return undefined;
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return undefined;
  return ["воскресенье", "понедельник", "вторник", "среда", "четверг", "пятница", "суббота"][date.getDay()];
}

export function selectTripEvents(
  items: EventInventoryItem[],
  brief: TripBrief,
  profile: PreferenceProfile,
  window: DateWindow,
  excludedIds: Set<string> = new Set(),
): EventInventoryItem[] {
  const insights = profile.behavioralInsights?.events;
  const signals = eventSearchInterests(brief, profile)
    .map(normalizeSignal)
    .filter(Boolean);
  const avoidedActivities = (brief.preferences?.activities ?? [])
    .filter((item) => item.polarity === "avoid")
    .map((item) => ({ value: normalizeSignal(item.value), strength: item.strength }));
  const scored = items
    .filter((item) => {
      if (excludedIds.has(item.eventId)) return false;
      const minimumAge = eventMinimumAge(item.ageRestriction);
      if (minimumAge === 18 && profile.behavioralInsights?.audience.adultContentAllowed === false) {
        return false;
      }
      const youngestChild = brief.travelers.childrenAges.length
        ? Math.min(...brief.travelers.childrenAges)
        : undefined;
      if (!(youngestChild === undefined || minimumAge === undefined || minimumAge <= youngestChild)) {
        return false;
      }
      const text = normalizeSignal([item.name, item.kind, ...(item.genres ?? [])].join(" "));
      return !avoidedActivities.some((activity) =>
        activity.strength === "hard" &&
        (text.includes(activity.value) || activity.value.includes(text)));
    })
    .map((item, index) => {
      const text = normalizeSignal([item.name, item.kind, ...(item.genres ?? [])].join(" "));
      const interestScore = signals.reduce(
        (sum, signal) => sum + (text.includes(signal) || signal.includes(text) ? 20 : 0),
        0,
      );
      const avoidanceScore = avoidedActivities.reduce((sum, activity) =>
        sum + (text.includes(activity.value) || activity.value.includes(text) ? -30 : 0), 0);
      const kindScore = (insights?.kindAffinities ?? []).reduce((sum, preference) => {
        const signal = normalizeSignal(preference.value);
        return sum + (text.includes(signal) || signal.includes(normalizeSignal(item.kind))
          ? Math.min(18, 6 + preference.evidenceCount * 2)
          : 0);
      }, 0);
      const genreScore = (insights?.genreAffinities ?? []).reduce((sum, preference) => {
        const signal = normalizeSignal(preference.value);
        return sum + (text.includes(signal) ? Math.min(16, 5 + preference.evidenceCount * 2) : 0);
      }, 0);
      const venueText = normalizeSignal(item.venue ?? "");
      const venueScore = (insights?.venueAffinities ?? []).reduce((sum, preference) => {
        const signal = normalizeSignal(preference.value);
        return sum + (venueText && (venueText.includes(signal) || signal.includes(venueText))
          ? Math.min(10, 3 + preference.evidenceCount)
          : 0);
      }, 0);
      const preferredDayParts = new Set(insights?.preferredDayParts.map((value) => normalizeSignal(value.value)) ?? []);
      const preferredWeekdays = new Set(insights?.preferredWeekdays.map((value) => normalizeSignal(value.value)) ?? []);
      const timeScore = (preferredDayParts.has(normalizeSignal(eventDayPart(item.dateTime) ?? "")) ? 4 : 0)
        + (preferredWeekdays.has(normalizeSignal(eventWeekday(item.dateTime) ?? "")) ? 4 : 0);
      const targetOrderRub = insights?.medianOrderRub ?? 0;
      const targetPartySize = Math.max(1, insights?.averagePartySize ?? 1);
      const targetPerPersonRub = targetOrderRub / targetPartySize;
      const priceScore = item.priceRub && targetPerPersonRub > 0
        ? Math.max(0, 8 - Math.abs(item.priceRub - targetPerPersonRub) / Math.max(500, targetPerPersonRub) * 8)
        : 0;
      const locationScore =
        item.latitude !== undefined && item.longitude !== undefined
          ? 30
          : item.address
            ? 20
            : item.venue
              ? 10
              : 0;
      return {
        item,
        index,
        score: interestScore + avoidanceScore + kindScore + genreScore + venueScore + timeScore + priceScore + locationScore + (item.rating ?? 0),
      };
    })
    .sort((left, right) =>
      right.score - left.score ||
      String(left.item.dateTime ?? "").localeCompare(String(right.item.dateTime ?? "")) ||
      left.index - right.index,
    );
  const selected: EventInventoryItem[] = [];
  const occupiedDays = new Set<string>();
  const selectedIds = new Set<string>();
  for (const { item } of scored) {
    const day = item.dateTime?.slice(0, 10);
    if (
      !day || day < window.startDate || day > window.endDate ||
      occupiedDays.has(day) || selectedIds.has(item.eventId)
    ) continue;
    occupiedDays.add(day);
    selectedIds.add(item.eventId);
    selected.push(item);
    if (selected.length >= targetEventCount(
      window.startDate,
      window.endDate,
      brief.preferences?.pace?.value,
    )) break;
  }
  return selected.sort((left, right) =>
    String(left.dateTime ?? "").localeCompare(String(right.dateTime ?? "")),
  );
}

function chooseCombinations(
  bundle: InventoryBundle,
  brief: TripBrief,
  profile: PreferenceProfile,
): CandidateSeed[] {
  const outbound = [...bundle.outbound].sort((a, b) => a.priceRub - b.priceRub).slice(0, 5);
  const inbound = [...bundle.inbound].sort((a, b) => a.priceRub - b.priceRub).slice(0, 5);
  const nights = daysBetween(bundle.window.startDate, bundle.window.endDate);
  const hotelRange = hotelNightlyPriceRange(profile.incomeCohort);
  const hotels = [...bundle.hotels]
    .filter((hotel) => {
      const nightlyPrice = hotel.priceRub / nights;
      return nightlyPrice >= hotelRange.minRub && nightlyPrice <= hotelRange.maxRub;
    })
    .sort((a, b) => a.priceRub - b.priceRub);
  const passengerCount = brief.travelers.adults + brief.travelers.childrenAges.length;
  const seeds: CandidateSeed[] = [];
  for (const outward of outbound) {
    for (const returning of inbound) {
      for (const hotel of hotels) {
        const dailySpendRub = profile.weekendAverageDailySpendRub > 0
          ? profile.weekendAverageDailySpendRub
          : 4_000;
        const estimates = (nights + 1) * dailySpendRub * passengerCount;
        seeds.push({
          bundle,
          outbound: outward,
          inbound: returning,
          hotel,
          projectedTotalRub:
            outward.priceRub + returning.priceRub + hotel.priceRub + estimates,
        });
      }
    }
  }
  return seeds.sort((left, right) => left.projectedTotalRub - right.projectedTotalRub);
}

export class TripCompiler {
  readonly #provider: PlannerDataProvider;
  readonly #editorial: EditorialService;
  readonly #weather: WeatherService;

  constructor(
    provider: PlannerDataProvider,
    editorial: EditorialService,
    weather: WeatherService = new UnavailableWeatherService(),
  ) {
    this.#provider = provider;
    this.#editorial = editorial;
    this.#weather = weather;
  }

  async compile(
    runId: string,
    brief: TripBrief,
    profile: PreferenceProfile,
    progress: CompilerProgress = {},
  ): Promise<CompileResult> {
    const origin = findCity(brief.originCityId);
    if (!origin) throw new Error("Город отправления не поддерживается");
    const explicitDestination = brief.destinationCityId ? findCity(brief.destinationCityId) : undefined;
    if (brief.destinationCityId && !explicitDestination) {
      throw new Error("Город назначения не поддерживается");
    }
    if (explicitDestination?.id === origin.id) throw new Error("Город назначения совпадает с городом отправления");

    const windows = dateWindows(brief);
    const possibleCities = explicitDestination
      ? [explicitDestination]
      : cities.filter((city) => city.id !== origin.id);
    const climateAssessments = new Map<string, ClimateAssessment>();
    // A fixed destination does not need weather to rank cities. Load it only
    // after the core flight + hotel proposal has been published.
    if (brief.preferences?.climate && !explicitDestination) {
      await Promise.all(possibleCities.flatMap((city) => windows.map(async (window) => {
        try {
          const weather = await this.#weather.forTrip(city, window);
          climateAssessments.set(climateKey(city, window), climateAssessment(weather, brief));
        } catch {
          climateAssessments.set(climateKey(city, window), {
            score: -40,
            hardViolationCount: brief.preferences?.climate?.strength === "hard" ? 1 : 0,
            reasons: [],
            available: false,
          });
        }
      })));
    }
    const rankedCities = possibleCities
      .map((city, index) => {
        const preferenceScores = cityPreferenceScores(city, brief, profile);
        const bestClimate = windows
          .map((window) => climateAssessments.get(climateKey(city, window)))
          .filter((value): value is ClimateAssessment => Boolean(value))
          .sort((left, right) =>
            left.hardViolationCount - right.hardViolationCount || right.score - left.score)[0];
        return {
          city,
          index,
          textPreferenceScore: preferenceScores.text + (bestClimate?.score ?? 0),
          profileScore: preferenceScores.profile,
          hardViolationCount: hardTagViolations(city, brief) + (bestClimate?.hardViolationCount ?? 0),
          climateAvailable: bestClimate?.available ?? !brief.preferences?.climate,
        };
      })
      .sort((left, right) =>
        left.hardViolationCount - right.hardViolationCount ||
        right.textPreferenceScore - left.textPreferenceScore ||
        right.profileScore - left.profileScore ||
        left.index - right.index);
    const desiredCount = explicitDestination ? 1 : Math.min(3, rankedCities.length);
    const strictCities = rankedCities.filter((item) => item.hardViolationCount === 0);
    const relaxedConstraints = strictCities.length < desiredCount;
    const shortlist = (relaxedConstraints ? rankedCities : strictCities)
      .slice(0, 5)
      .map(({ city }) => city);
    const constraintWarnings = [
      ...(relaxedConstraints && rankedCities.some((item) => item.hardViolationCount > 0)
        ? ["Жёстким пожеланиям соответствует меньше трёх направлений; добавлены ближайшие варианты с явным отклонением."]
        : []),
      ...(brief.preferences?.climate && rankedCities.every((item) => !item.climateAvailable)
        ? ["Пожелание по климату не удалось проверить: погодные данные временно недоступны."]
        : []),
    ];
    progress.shortlist?.(shortlist);

    const progressiveSearch = Boolean(explicitDestination && windows.length > 1);
    const progressiveSeeds: CandidateSeed[] = [];
    const progressivePartials: TripProposal[] = [];
    const progressiveEnrichments: Array<Promise<TripProposal>> = [];
    const publishProgressiveBundle = (bundle: InventoryBundle) => {
      if (!progressiveSearch || progressiveSeeds.length >= 3) return;
      const options = chooseCombinations(bundle, brief, profile);
      const seed = this.#progressiveCandidate(
        options,
        progressiveSeeds,
        profile,
        brief.budgetRub,
      );
      if (!seed) return;
      const index = progressiveSeeds.length;
      const tier = this.#tier(seed, index, profile, brief.budgetRub);
      const partial = this.#buildBaseProposal(runId, brief, profile, seed, tier);
      progressiveSeeds.push(seed);
      progressivePartials.push(partial);
      progress.partial?.(partial);
      progressiveEnrichments.push(this.#buildProposal(brief, profile, seed, partial));
    };

    const searches = await Promise.all(
      shortlist.map((city) => this.#availableBundles(
        origin,
        city,
        windows,
        brief,
        profile,
        progress,
        climateAssessments,
        {
          parallelWindows: progressiveSearch,
          ...(progressiveSearch ? { onBundle: publishProgressiveBundle } : {}),
        },
      )),
    );
    const bundles = searches.flatMap((result) => result.bundles);
    const attemptWarnings = unique(searches.flatMap((result) => result.warnings));
    if (bundles.length === 0) {
      const reason = attemptWarnings.length ? `: ${attemptWarnings.join(" | ")}` : "";
      throw new Error(`Не удалось найти ни одной полной комбинации перелёта и отеля${reason}`);
    }

    const allWarnings = unique([
      ...constraintWarnings,
      ...attemptWarnings,
      ...bundles.flatMap((bundle) => bundle.warnings),
    ]);
    let selected: CandidateSeed[];
    if (explicitDestination) {
      const options = bundles.flatMap((bundle) => chooseCombinations(bundle, brief, profile));
      if (progressiveSearch) {
        selected = [...progressiveSeeds];
        while (selected.length < 3) {
          const candidate = this.#progressiveCandidate(options, selected, profile, brief.budgetRub);
          if (!candidate) break;
          selected.push(candidate);
        }
      } else {
        selected = this.#selectSameCity(options, profile, brief.budgetRub);
      }
    } else {
      const options = bundles.flatMap((bundle) => chooseCombinations(bundle, brief, profile));
      selected = this.#selectDifferentCities(
        options,
        profile,
        brief.budgetRub,
      );
    }

    if (selected.length === 0) {
      const range = hotelNightlyPriceRange(profile.incomeCohort);
      throw new Error(
        `Не нашли отели в персональном диапазоне ${range.minRub.toLocaleString("ru-RU")}–${range.maxRub.toLocaleString("ru-RU")} ₽ за ночь`,
      );
    }

    const withinBudgetCount = brief.budgetRub
      ? selected.filter((seed) => seed.projectedTotalRub <= brief.budgetRub!).length
      : selected.length;
    if (brief.budgetRub && withinBudgetCount < 3) {
      allWarnings.push(
        `В лимит ${brief.budgetRub.toLocaleString("ru-RU")} ₽ удалось честно уложить только ${withinBudgetCount} вариант(а); дополнительно показан ближайший вариант выше лимита.`,
      );
    }
    if (!brief.budgetRub && selected.length < 3) {
      allWarnings.push(
        `В персональном ценовом диапазоне найдено только ${selected.length} уникальных вариант(а) отеля.`,
      );
    }

    const partials = selected.map((seed, index) => {
      const existingIndex = progressiveSeeds.indexOf(seed);
      if (existingIndex >= 0) return progressivePartials[existingIndex]!;
      const proposal = this.#buildBaseProposal(
        runId,
        brief,
        profile,
        seed,
        this.#tier(seed, index, profile, brief.budgetRub),
      );
      progress.partial?.(proposal);
      return proposal;
    });

    const enriched = await Promise.all(
      selected.map((seed, index) => {
        const existingIndex = progressiveSeeds.indexOf(seed);
        return existingIndex >= 0
          ? progressiveEnrichments[existingIndex]!
          : this.#buildProposal(brief, profile, seed, partials[index]!);
      }),
    );
    const decorated = await this.#editorial.decorate(enriched, profile, brief);
    const editorialCheckedAt = new Date().toISOString();
    const proposals = decorated.proposals.map((proposal) => ({
      ...proposal,
      sources: proposal.sources.map((source) =>
        source.component === "editorial"
          ? {
              ...source,
              availability: "available" as const,
              source: decorated.usedFallback ? "Локальный редактор" : "LLM Proxy",
              checkedAt: editorialCheckedAt,
            }
          : source,
      ),
    }));
    return { proposals, warnings: unique(allWarnings) };
  }

  async #availableBundles(
    origin: City,
    city: City,
    windows: DateWindow[],
    brief: TripBrief,
    profile: PreferenceProfile,
    progress: CompilerProgress,
    climateAssessments: Map<string, ClimateAssessment>,
    options: BundleSearchOptions = {},
  ): Promise<BundleSearchResult> {
    const load = (window: DateWindow) => this.#availableWindow(
      origin,
      city,
      window,
      brief,
      profile,
      progress,
      climateAssessments,
    );
    if (options.parallelWindows) {
      const settled = await Promise.allSettled(windows.map(async (window) => {
        const entry = await load(window);
        for (const bundle of entry.bundles) options.onBundle?.(bundle);
        return entry;
      }));
      const result: BundleSearchResult = { bundles: [], warnings: [] };
      for (const entry of settled) {
        if (entry.status === "rejected") {
          result.warnings.push(
            `${city.name}: ${entry.reason instanceof Error ? entry.reason.message : "ошибка проверки дат"}`,
          );
          continue;
        }
        result.bundles.push(...entry.value.bundles);
        result.warnings.push(...entry.value.warnings);
      }
      return result;
    }

    const bundles: InventoryBundle[] = [];
    const attemptWarnings: string[] = [];
    for (const window of windows) {
      const result = await load(window);
      bundles.push(...result.bundles);
      attemptWarnings.push(...result.warnings);
    }
    return { bundles, warnings: attemptWarnings };
  }

  async #availableWindow(
    origin: City,
    city: City,
    window: DateWindow,
    brief: TripBrief,
    profile: PreferenceProfile,
    progress: CompilerProgress,
    climateAssessments: Map<string, ClimateAssessment>,
  ): Promise<BundleSearchResult> {
    const assessment = climateAssessments.get(climateKey(city, window)) ?? {
      score: 0,
      hardViolationCount: 0,
      reasons: [],
      available: true,
    };
    progress.candidate?.(city, `Проверяем ${window.startDate}—${window.endDate}`);
    const [outboundEntry, inboundEntry, hotelEntry] = await Promise.allSettled([
      this.#provider.flights(origin, city, window.startDate, brief.travelers),
      this.#provider.flights(city, origin, window.endDate, brief.travelers),
      this.#provider.hotels(city, window, brief.travelers),
    ]);
    if (
      outboundEntry.status === "rejected" ||
      inboundEntry.status === "rejected" ||
      hotelEntry.status === "rejected"
    ) {
      const failures = [
        ...(outboundEntry.status === "rejected"
          ? [`рейс туда: ${this.#errorMessage(outboundEntry.reason)}`]
          : []),
        ...(inboundEntry.status === "rejected"
          ? [`рейс обратно: ${this.#errorMessage(inboundEntry.reason)}`]
          : []),
        ...(hotelEntry.status === "rejected"
          ? [`отели: ${this.#errorMessage(hotelEntry.reason)}`]
          : []),
      ];
      const reason = failures.join(", ");
      progress.candidate?.(city, `Не подошло: ${reason}`);
      return {
        bundles: [],
        warnings: [`${city.name} ${window.startDate}—${window.endDate}: ${reason}`],
      };
    }
    const outbound = outboundEntry.value;
    const inbound = inboundEntry.value;
    const hotels = hotelEntry.value;
    const unavailable = [
      ...(outbound.data.length === 0 ? ["нет рейсов туда"] : []),
      ...(inbound.data.length === 0 ? ["нет рейсов обратно"] : []),
      ...(hotels.data.length === 0 ? ["нет отелей"] : []),
    ];
    if (unavailable.length > 0) {
      const reason = unavailable.join(", ");
      progress.candidate?.(city, `Не подошло: ${reason}`);
      return {
        bundles: [],
        warnings: [`${city.name} ${window.startDate}—${window.endDate}: ${reason}`],
      };
    }
    const preferenceScores = cityPreferenceScores(city, brief, profile);
    const bundle: InventoryBundle = {
      city,
      window,
      outbound: outbound.data,
      inbound: inbound.data,
      hotels: hotels.data,
      warnings: unique([...outbound.warnings, ...inbound.warnings, ...hotels.warnings]),
      sources: [
        {
          component: "flights",
          availability: "available",
          required: true,
          source: unique([outbound.source, inbound.source]).join(" + "),
          checkedAt: [outbound.checkedAt, inbound.checkedAt].sort().at(-1) ?? outbound.checkedAt,
        },
        sourceStatus("hotel", true, hotels, "Отели не найдены"),
      ],
      textPreferenceScore: preferenceScores.text + assessment.score,
      profileScore: preferenceScores.profile,
      hardViolationCount: hardTagViolations(city, brief) + assessment.hardViolationCount,
      preferenceReasons: unique([
        ...destinationPreferenceReasons(city, brief),
        ...assessment.reasons,
      ]),
    };
    progress.candidate?.(city, `Данные готовы для ${window.startDate}—${window.endDate}`);
    return { bundles: [bundle], warnings: [] };
  }

  #progressiveCandidate(
    options: CandidateSeed[],
    selected: CandidateSeed[],
    profile: PreferenceProfile,
    budgetRub?: number,
  ): CandidateSeed | undefined {
    const usedHotelIds = new Set(selected.map((seed) => seed.hotel.hotelId));
    let candidates = options.filter((option) => !usedHotelIds.has(option.hotel.hotelId));
    if (budgetRub) {
      const withinBudget = candidates.filter((option) => option.projectedTotalRub <= budgetRub);
      if (withinBudget.length > 0) {
        candidates = withinBudget;
      } else {
        const alreadyHasClosestOver = selected.some((option) => option.projectedTotalRub > budgetRub);
        if (alreadyHasClosestOver) return undefined;
        return candidates
          .filter((option) => option.projectedTotalRub > budgetRub)
          .sort((left, right) => left.projectedTotalRub - right.projectedTotalRub)[0];
      }
    }
    const target = cohortTargets(profile)[Math.min(selected.length, 2)]!;
    return [...candidates].sort((left, right) =>
      left.bundle.hardViolationCount - right.bundle.hardViolationCount ||
      right.bundle.textPreferenceScore - left.bundle.textPreferenceScore ||
      right.bundle.profileScore - left.bundle.profileScore ||
      hotelPreferenceScore(right.hotel, profile) - hotelPreferenceScore(left.hotel, profile) ||
      Math.abs(hotelNightlyPrice(left) - target.amountRub) -
        Math.abs(hotelNightlyPrice(right) - target.amountRub) ||
      left.projectedTotalRub - right.projectedTotalRub,
    )[0];
  }

  #tier(
    seed: CandidateSeed,
    index: number,
    profile: PreferenceProfile,
    budgetRub?: number,
  ): TripProposal["tier"] {
    if (budgetRub) {
      return seed.projectedTotalRub <= budgetRub ? "within_budget" : "closest_over_budget";
    }
    return cohortTargets(profile)[index]?.position ?? "cohort_typical";
  }

  #errorMessage(error: unknown): string {
    return error instanceof Error ? error.message : "ошибка источника";
  }

  #selectByCohort(
    options: CandidateSeed[],
    profile: PreferenceProfile,
    distinctCities: boolean,
  ): CandidateSeed[] {
    const selected: CandidateSeed[] = [];
    const hotelIds = new Set<string>();
    const cityIds = new Set<string>();
    for (const target of cohortTargets(profile)) {
      const candidate = [...options]
        .filter((option) => !hotelIds.has(option.hotel.hotelId))
        .filter((option) => !distinctCities || !cityIds.has(option.bundle.city.id))
        .sort((left, right) =>
          left.bundle.hardViolationCount - right.bundle.hardViolationCount ||
          right.bundle.textPreferenceScore - left.bundle.textPreferenceScore ||
          right.bundle.profileScore - left.bundle.profileScore ||
          hotelPreferenceScore(right.hotel, profile) - hotelPreferenceScore(left.hotel, profile) ||
          Math.abs(hotelNightlyPrice(left) - target.amountRub) -
            Math.abs(hotelNightlyPrice(right) - target.amountRub) ||
          left.projectedTotalRub - right.projectedTotalRub,
        )[0];
      if (!candidate) continue;
      selected.push(candidate);
      hotelIds.add(candidate.hotel.hotelId);
      cityIds.add(candidate.bundle.city.id);
    }
    return selected;
  }

  #selectSameCity(
    options: CandidateSeed[],
    profile: PreferenceProfile,
    budgetRub?: number,
  ): CandidateSeed[] {
    const eligible = budgetRub ? options.filter((option) => option.projectedTotalRub <= budgetRub) : options;
    if (budgetRub && eligible.length < 3) {
      const closestOver = options.find((option) => option.projectedTotalRub > budgetRub);
      return [
        ...this.#selectByCohort(eligible, profile, false),
        ...(closestOver ? [closestOver] : []),
      ].slice(0, 3);
    }
    if (eligible.length === 0) return [];
    return this.#selectByCohort(eligible, profile, false);
  }

  #selectDifferentCities(
    options: CandidateSeed[],
    profile: PreferenceProfile,
    budgetRub?: number,
  ): CandidateSeed[] {
    const sorted = options
      .filter((option): option is CandidateSeed => Boolean(option))
      .sort((left, right) => left.projectedTotalRub - right.projectedTotalRub);
    const eligible = budgetRub
      ? sorted.filter((option) => option.projectedTotalRub <= budgetRub)
      : sorted;
    if (budgetRub) {
      const selected = this.#selectByCohort(eligible, profile, true);
      if (selected.length >= 3) return selected;
      const selectedCities = new Set(selected.map((option) => option.bundle.city.id));
      const closestOver = sorted.find((option) =>
        option.projectedTotalRub > budgetRub && !selectedCities.has(option.bundle.city.id));
      return [...selected, ...(closestOver ? [closestOver] : [])];
    }
    return this.#selectByCohort(eligible, profile, true);
  }

  #buildBaseProposal(
    runId: string,
    brief: TripBrief,
    profile: PreferenceProfile,
    seed: CandidateSeed,
    tier: TripProposal["tier"],
  ): TripProposal {
    const flightStatus = seed.bundle.sources.find((source) => source.component === "flights")!;
    const hotelStatus = seed.bundle.sources.find((source) => source.component === "hotel")!;
    const profileStatus: SourceStatus = {
      component: "profile",
      availability: profile.source === "bank" ? "available" : "unavailable",
      required: false,
      source: profile.source === "bank" ? "T-Bank" : "Нейтральный профиль",
      checkedAt: profile.generatedAt,
      ...(profile.source === "fallback" ? { message: "Банковская персонализация недоступна" } : {}),
    };
    const people = brief.travelers.adults + brief.travelers.childrenAges.length;
    const nights = daysBetween(seed.bundle.window.startDate, seed.bundle.window.endDate);
    const fallbackDailySpendPerPerson = tier === "cohort_floor" || tier === "economy"
      ? 2_000
      : tier === "cohort_ceiling" || tier === "comfort"
        ? 6_800
        : 4_000;
    const dailySpendPerPerson = profile.weekendAverageDailySpendRub > 0
      ? profile.weekendAverageDailySpendRub
      : fallbackDailySpendPerPerson;
    const estimateTimestamp = new Date().toISOString();
    const outboundPrice = priceOf(seed.outbound);
    const returnPrice = priceOf(seed.inbound);
    const hotelPrice = priceOf(seed.hotel);
    const dailySpendPrice: Price = {
      amount: dailySpendPerPerson * people * (nights + 1),
      currency: "RUB",
      kind: "estimated",
      source: profile.weekendAverageDailySpendRub > 0
        ? "Средние траты клиента в выходной"
        : "Оценка Travel Nova",
      checkedAt: estimateTimestamp,
    };
    const hotelPoint: MapPoint = {
      id: `hotel-${seed.hotel.hotelId}`,
      type: "hotel",
      name: seed.hotel.name,
      latitude: seed.hotel.latitude ?? seed.bundle.city.latitude,
      longitude: seed.hotel.longitude ?? seed.bundle.city.longitude,
      ...(seed.hotel.address ? { subtitle: seed.hotel.address } : {}),
      ...(seed.hotel.image ? { image: seed.hotel.image } : {}),
    };
    const flight = (
      inventory: FlightInventoryItem,
      direction: FlightOption["direction"],
      from: string,
      to: string,
      date: string,
    ): FlightOption => ({
      ...(inventory.offerId ? { offerId: inventory.offerId } : {}),
      direction,
      fromCode: from,
      toCode: to,
      date,
      summary: inventory.summary,
      ...(inventory.departureTime ? { departureTime: inventory.departureTime } : {}),
      ...(inventory.arrivalTime ? { arrivalTime: inventory.arrivalTime } : {}),
      price: priceOf(inventory),
      availability: flightStatus,
    });
    const hotel: HotelOption = {
      hotelId: seed.hotel.hotelId,
      name: seed.hotel.name,
      stars: seed.hotel.stars,
      ...(seed.hotel.address ? { address: seed.hotel.address } : {}),
      ...(seed.hotel.rating !== undefined ? { rating: seed.hotel.rating } : {}),
      ...(seed.hotel.meal ? { meal: seed.hotel.meal } : {}),
      ...(seed.hotel.image ? { image: seed.hotel.image } : {}),
      price: hotelPrice,
      mapPoint: hotelPoint,
      availability: hotelStatus,
    };
    const priceBreakdown = [
      { label: "Перелёт туда", price: outboundPrice },
      { label: "Перелёт обратно", price: returnPrice },
      { label: `${nights} ноч. в отеле`, price: hotelPrice },
      { label: "Траты на месте", price: dailySpendPrice },
    ];
    const liveSubtotalRub = priceBreakdown
      .filter((item) => item.price.kind === "live")
      .reduce((sum, item) => sum + item.price.amount, 0);
    const estimatedSubtotalRub = priceBreakdown
      .filter((item) => item.price.kind === "estimated")
      .reduce((sum, item) => sum + item.price.amount, 0);
    const total = liveSubtotalRub + estimatedSubtotalRub;
    return {
      id: randomUUID(),
      runId,
      title: fallbackTripTitle(tier, seed.bundle.city.name),
      tagline: seed.bundle.city.accent,
      tier,
      destination: seed.bundle.city,
      startDate: seed.bundle.window.startDate,
      endDate: seed.bundle.window.endDate,
      travelers: brief.travelers,
      flights: {
        outbound: flight(
          seed.outbound,
          "outbound",
          findCity(brief.originCityId)?.iata ?? "",
          seed.bundle.city.iata,
          seed.bundle.window.startDate,
        ),
        return: flight(
          seed.inbound,
          "return",
          seed.bundle.city.iata,
          findCity(brief.originCityId)?.iata ?? "",
          seed.bundle.window.endDate,
        ),
      },
      hotel,
      events: [],
      restaurantGroups: [],
      itinerary: this.#itinerary(
        seed.bundle.window,
        hotelPoint,
        [],
        [],
        brief.preferences?.pace?.value,
      ),
      weather: { days: [] },
      mapPoints: [hotelPoint],
      priceBreakdown,
      totalPrice: {
        amount: total,
        currency: "RUB",
        kind: estimatedSubtotalRub > 0 ? "estimated" : "live",
        source: "Предварительный расчёт Travel Nova",
        checkedAt: estimateTimestamp,
      },
      liveSubtotalRub,
      estimatedSubtotalRub,
      fitReasons: this.#fitReasons(seed.bundle, profile, brief),
      warnings: unique(seed.bundle.warnings),
      generatedAt: estimateTimestamp,
      dataMode: this.#provider.dataMode,
      completeness: "partial",
      sources: [profileStatus, flightStatus, hotelStatus],
    };
  }

  async #buildProposal(
    brief: TripBrief,
    profile: PreferenceProfile,
    seed: CandidateSeed,
    base: TripProposal,
  ): Promise<TripProposal> {
    const eventPromise = this.#provider
      .events(seed.bundle.city, seed.bundle.window, eventSearchInterests(brief, profile))
      .catch((error): ProviderResult<EventInventoryItem[]> => ({
        data: [],
        warnings: [
          `Афиша ${seed.bundle.city.name}: ${error instanceof Error ? error.message : "источник недоступен"}`,
        ],
        isFallback: false,
        source: "T-Bank Afisha",
        checkedAt: new Date().toISOString(),
      }));
    const weatherPromise = this.#weather
      .forTrip(seed.bundle.city, seed.bundle.window)
      .catch((error): WeatherLookupResult => ({
        data: { days: [] },
        warnings: [
          `Погода для ${seed.bundle.city.name} недоступна: ${error instanceof Error ? error.message : "ошибка источника"}`,
        ],
        available: false,
        source: "Open-Meteo",
        checkedAt: new Date().toISOString(),
      }));
    type AnchorSearch = {
      groupId: string;
      anchor: NearbyAnchor;
      anchorName: string;
      anchorMapPointId?: string;
      includePointsOfInterest: boolean;
      placeKinds?: Array<"culture" | "nature" | "nightlife">;
    };
    const loadNearby = async (search: AnchorSearch) => {
      try {
        const result = await this.#provider.nearby(seed.bundle.city, search.anchor, {
          includePointsOfInterest: search.includePointsOfInterest,
          ...(search.placeKinds ? { placeKinds: search.placeKinds } : {}),
        });
        return { search, result };
      } catch (error) {
        const checkedAt = new Date().toISOString();
        return {
          search,
          result: {
            data: [],
            warnings: [
              `Места рядом с «${search.anchorName}» недоступны: ${error instanceof Error ? error.message : "ошибка источника"}`,
            ],
            isFallback: false,
            source: "OpenStreetMap",
            checkedAt,
          } satisfies ProviderResult<NearbyPlace[]>,
        };
      }
    };
    const hotelSearch: AnchorSearch = {
      groupId: `restaurants-hotel-${seed.hotel.hotelId}`,
      anchor: {
        id: seed.hotel.hotelId,
        type: "hotel",
        name: seed.hotel.name,
        ...(seed.hotel.address ? { address: seed.hotel.address } : {}),
        ...(seed.hotel.latitude !== undefined ? { latitude: seed.hotel.latitude } : {}),
        ...(seed.hotel.longitude !== undefined ? { longitude: seed.hotel.longitude } : {}),
      },
      anchorName: seed.hotel.name,
      anchorMapPointId: base.hotel.mapPoint.id,
      includePointsOfInterest: true,
      placeKinds: nearbyPlaceKinds(brief),
    };
    const [eventResult, weather, hotelNearbyEntry] = await Promise.all([
      eventPromise,
      weatherPromise,
      loadNearby(hotelSearch),
    ]);
    const people = brief.travelers.adults + brief.travelers.childrenAges.length;
    const selectedEvents = selectTripEvents(
      eventResult.data,
      brief,
      profile,
      seed.bundle.window,
    );
    const events = selectedEvents.map((event) => this.#event(event, people));
    const eventSearches: AnchorSearch[] = events.map((event) => ({
      groupId: `restaurants-event-${event.eventId}`,
      anchor: {
        id: event.eventId,
        type: "event" as const,
        name: event.venue ?? event.name,
        ...(event.address ? { address: event.address } : {}),
        ...(event.mapPoint ? { latitude: event.mapPoint.latitude, longitude: event.mapPoint.longitude } : {}),
      },
      anchorName: event.name,
      ...(event.mapPoint ? { anchorMapPointId: event.mapPoint.id } : {}),
      includePointsOfInterest: false,
    }));
    const nearbyResults = [hotelNearbyEntry, ...(await Promise.all(eventSearches.map(loadNearby)))];
    const restaurantGroups: RestaurantGroup[] = nearbyResults.map(({ search, result }) =>
      this.#restaurantGroup(search, result, profile, brief),
    );
    const hotelNearby = nearbyResults[0]?.result;
    const pointsOfInterest = (hotelNearby?.data ?? [])
      .filter((place) => place.type === "poi")
      .slice(0, 6)
      .map((place) => this.#mapPoint(
        place,
        `${placeCategoryLabel(place.category)} · ${place.distanceMeters} м от отеля`,
      ));
    const nearbyCheckedAt = nearbyResults
      .map(({ result }) => result.checkedAt)
      .sort()
      .at(-1) ?? new Date().toISOString();
    const nearbyAvailable = restaurantGroups.some((group) => group.restaurants.length > 0) || pointsOfInterest.length > 0;
    const nearbyStatus: SourceStatus = {
      component: "nearby",
      availability: nearbyAvailable ? "available" : "unavailable",
      required: false,
      source: unique(nearbyResults.map(({ result }) => result.source)).join(" + ") || "OpenStreetMap",
      checkedAt: nearbyCheckedAt,
      ...(!nearbyAvailable ? { message: "Рестораны и достопримечательности рядом не найдены" } : {}),
    };
    const estimateTimestamp = new Date().toISOString();
    const priceBreakdown = [
      ...base.priceBreakdown.slice(0, 3),
      ...events.flatMap((event) => event.price ? [{ label: `Событие: ${event.name}`, price: event.price }] : []),
      ...base.priceBreakdown.slice(3),
    ];
    const liveSubtotalRub = priceBreakdown
      .filter((item) => item.price.kind === "live")
      .reduce((sum, item) => sum + item.price.amount, 0);
    const estimatedSubtotalRub = priceBreakdown
      .filter((item) => item.price.kind === "estimated")
      .reduce((sum, item) => sum + item.price.amount, 0);
    const total = liveSubtotalRub + estimatedSubtotalRub;
    const eventStatus: SourceStatus = {
      ...sourceStatus("event", false, eventResult, "Подходящие события не найдены"),
      availability: events.length > 0 ? "available" : "unavailable",
      ...(events.length === 0 ? { message: "Подходящие события в разные дни не найдены" } : {}),
    };
    const mapPoints = this.#uniqueMapPoints([
      base.hotel.mapPoint,
      ...restaurantGroups.flatMap((group) => group.restaurants.map((restaurant) => restaurant.mapPoint)),
      ...pointsOfInterest,
      ...events.flatMap((event) => event.mapPoint ? [event.mapPoint] : []),
    ]);
    const warnings = unique([
      ...base.warnings,
      ...eventResult.warnings,
      ...nearbyResults.flatMap(({ result }) => result.warnings),
      ...weather.warnings,
      ...(events.length < targetEventCount(base.startDate, base.endDate, brief.preferences?.pace?.value)
        ? [`Целевое количество событий: ${targetEventCount(base.startDate, base.endDate, brief.preferences?.pace?.value)}; в разные дни найдено: ${events.length}.`]
        : []),
      ...(brief.budgetRub && total > brief.budgetRub
        ? [`Расчёт превышает бюджет на ${(total - brief.budgetRub).toLocaleString("ru-RU")} ₽.`]
        : []),
    ]);
    const sources: SourceStatus[] = [
      ...base.sources,
      eventStatus,
      nearbyStatus,
      {
        component: "weather",
        availability: weather.available ? "available" : "unavailable",
        required: false,
        source: weather.source,
        checkedAt: weather.checkedAt,
        ...(!weather.available ? { message: "Погода для дат поездки пока недоступна" } : {}),
      },
      {
        component: "editorial",
        availability: "available",
        required: false,
        source: "LLM Proxy или локальный редактор",
        checkedAt: estimateTimestamp,
      },
    ];
    const completeness = sources.some(
      (source) => !source.required && source.availability === "unavailable",
    )
      ? "partial"
      : "complete";
    return {
      ...base,
      tier: brief.budgetRub
        ? total <= brief.budgetRub ? "within_budget" : "closest_over_budget"
        : base.tier,
      events,
      restaurantGroups,
      itinerary: this.#itinerary(
        seed.bundle.window,
        base.hotel.mapPoint,
        pointsOfInterest,
        events,
        brief.preferences?.pace?.value,
      ),
      weather: weather.data,
      mapPoints,
      priceBreakdown,
      totalPrice: {
        amount: total,
        currency: "RUB",
        kind: estimatedSubtotalRub > 0 ? "estimated" : "live",
        source: "Сводный расчёт Travel Nova",
        checkedAt: estimateTimestamp,
      },
      liveSubtotalRub,
      estimatedSubtotalRub,
      warnings,
      generatedAt: estimateTimestamp,
      dataMode: this.#provider.dataMode,
      completeness,
      sources,
    };
  }

  #restaurantGroup(
    search: {
      groupId: string;
      anchor: NearbyAnchor;
      anchorName: string;
      anchorMapPointId?: string;
    },
    result: ProviderResult<NearbyPlace[]>,
    profile: PreferenceProfile,
    brief: TripBrief,
  ): RestaurantGroup {
    const interestSignals = (brief.interests ?? []).map(normalizeSignal).filter(Boolean);
    const diningMerchants = profile.favoriteDiningMerchants.map(normalizeSignal).filter(Boolean);
    const preferredCuisines = profile.diningProfile.preferredCuisines.map(normalizeSignal).filter(Boolean);
    const restaurants = result.data
      .filter((place) => place.type === "restaurant")
      .map((place, index) => {
        const name = normalizeSignal(place.name);
        const cuisine = normalizeSignal(place.cuisine ?? "");
        const favorite = diningMerchants.some((merchant) =>
          merchant.length >= 4 && name.length >= 4 &&
          (merchant === name || merchant.includes(name) || name.includes(merchant)),
        );
        const explicitCuisineMatch = Boolean(cuisine) && interestSignals.some((signal) =>
          cuisine.includes(signal) || signal.includes(cuisine),
        );
        const profileCuisineMatch = Boolean(cuisine) && preferredCuisines.some((signal) =>
          cuisine.includes(signal) || signal.includes(cuisine),
        );
        return {
          place,
          index,
          score: (favorite ? 10_000 : 0) + (explicitCuisineMatch ? 1_000 : 0) +
            (profileCuisineMatch ? 750 : 0) - place.distanceMeters,
          reasons: [
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
      .map(({ place, reasons }) => this.#restaurant(place, reasons));
    const availability: SourceStatus = {
      component: "nearby",
      availability: restaurants.length > 0 ? "available" : "unavailable",
      required: false,
      source: result.source,
      checkedAt: result.checkedAt,
      ...(restaurants.length === 0 ? { message: `Рестораны рядом с «${search.anchorName}» не найдены` } : {}),
    };
    return {
      id: search.groupId,
      anchorType: search.anchor.type,
      anchorId: search.anchor.id,
      anchorName: search.anchorName,
      ...(search.anchorMapPointId ? { anchorMapPointId: search.anchorMapPointId } : {}),
      availability,
      restaurants,
    };
  }

  #restaurant(place: NearbyPlace, matchReasons: string[]): Restaurant {
    return {
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
      mapPoint: this.#mapPoint(place, place.cuisine ? `Кухня: ${place.cuisine}` : "Ресторан"),
      availability: {
        component: "nearby",
        availability: "available",
        required: false,
        source: place.source,
        checkedAt: place.checkedAt,
      },
    };
  }

  #mapPoint(place: NearbyPlace, subtitle?: string): MapPoint {
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

  #uniqueMapPoints(points: MapPoint[]): MapPoint[] {
    return [...new Map(points.map((point) => [point.id, point])).values()];
  }

  #event(item: EventInventoryItem, people: number): EventOption {
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
              currency: "RUB",
              kind: "live",
              source: item.source,
              checkedAt: item.checkedAt,
              expiresAt: new Date(Date.parse(item.checkedAt) + 15 * 60_000).toISOString(),
            },
          }
        : {}),
      ...(mapPoint ? { mapPoint } : {}),
      availability: {
        component: "event",
        availability: "available",
        required: false,
        source: item.source,
        checkedAt: item.checkedAt,
      },
    };
  }

  #itinerary(
    window: DateWindow,
    hotel: MapPoint,
    pointsOfInterest: MapPoint[],
    events: EventOption[],
    pace: TripPace = "balanced",
  ): ItineraryItem[] {
    const nights = daysBetween(window.startDate, window.endDate);
    const items: ItineraryItem[] = [
      {
        id: randomUUID(),
        day: 1,
        time: "После прилёта",
        title: "Заселиться и почувствовать район",
        description: `Спокойный старт рядом с ${hotel.name}.`,
        mapPointId: hotel.id,
      },
    ];
    const poiLimit = pace === "relaxed" ? 1 : pace === "active" ? 3 : 2;
    for (const [index, point] of pointsOfInterest.slice(0, poiLimit).entries()) {
      items.push({
        id: randomUUID(),
        day: Math.min(index + 2, nights + 1),
        time: "11:00",
        title: point.name,
        description: point.subtitle ?? "Главная точка дневной прогулки.",
        mapPointId: point.id,
      });
    }
    for (const event of events) {
      const eventDay = event.dateTime
        ? Math.max(1, Math.min(nights + 1, Math.floor((Date.parse(event.dateTime) - Date.parse(window.startDate)) / DAY_MS) + 1))
        : Math.min(2, nights + 1);
      items.push({
        id: randomUUID(),
        day: eventDay,
        time: event.dateTime?.slice(11, 16) || "19:00",
        title: event.name,
        description: "Событие из афиши; источник и расписание указаны в предупреждениях и должны быть перепроверены перед покупкой.",
        ...(event.mapPoint ? { mapPointId: event.mapPoint.id } : {}),
      });
    }
    items.push({
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
    return items.sort((left, right) =>
      left.day - right.day || timeOrder(left.time) - timeOrder(right.time),
    );
  }

  #fitReasons(bundle: InventoryBundle, profile: PreferenceProfile, brief: TripBrief): string[] {
    const city = bundle.city;
    const interests = brief.interests ?? [];
    const matches = city.tags.filter((tag) =>
      [...interests, ...profile.preferredCategories, ...profile.eventInterests].some((signal) =>
        signal.toLocaleLowerCase("ru").includes(tag),
      ),
    );
    return unique([
      ...bundle.preferenceReasons,
      ...(matches[0] ? [`Совпадает с интересом «${matches[0]}».`] : []),
      profile.diningSpendRub > 0
        ? "В программе есть локальная гастрономия рядом с отелем."
        : "Маршрут собран компактно вокруг отеля.",
      brief.preset === "event"
        ? "Поездка строится вокруг события и оставляет время на город."
        : brief.preferences?.pace
          ? `Маршрут учитывает ${paceLabel(brief.preferences.pace.value)}.`
          : "Темп подходит для выбранного формата поездки.",
    ]).slice(0, 4);
  }
}

export const tripDateWindows = dateWindows;
