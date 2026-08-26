import type { BehavioralInsights, RankedPreference } from "@travel-growth-inspiration/contracts";

import type {
  AudienceProfileData,
  EventOrderDetailsData,
  TravelOrderDetailsData,
} from "./tbank-json-contracts.js";
import type { ProfileOperation } from "./customer-profile.js";

export type OrderSignal = {
  orderId: string;
  objectType: string;
  status: string;
  amount?: number | string | null | undefined;
  createdAt: string;
  title: string;
  eventName: string;
  hotelName: string;
  destination: string;
};

const LEISURE_PATTERN = /афиш|развлеч|концерт|театр|спектак|кино|музе|выстав|стендап|цирк|фестивал|клуб|боулинг|квест|караоке|билет|event|entertain|concert|theatre|cinema|museum|exhibition|stand.?up|festival/iu;
const TRAVEL_PATTERN = /avia|flight|hotel|train|travel|авиа|перел[её]т|отел|гостиниц|поезд|жд|путешеств/iu;
const REJECTED_STATUS = /cancel|refund|fail|reject|declin|отмен|возврат|ошиб/iu;
const WEEKDAYS = ["воскресенье", "понедельник", "вторник", "среда", "четверг", "пятница", "суббота"];

function numeric(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number(String(value ?? "").replace(",", "."));
  return Number.isFinite(parsed) ? Math.abs(parsed) : 0;
}

function average(values: number[]): number {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

function median(values: number[]): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[middle] ?? 0
    : ((sorted[middle - 1] ?? 0) + (sorted[middle] ?? 0)) / 2;
}

function round(value: number): number {
  return Math.max(0, Math.round(value));
}

function validDate(value: string | undefined): Date | undefined {
  if (!value) return undefined;
  const parsed = new Date(value);
  return Number.isFinite(parsed.getTime()) ? parsed : undefined;
}

function weekday(value: string | undefined): string | undefined {
  const date = validDate(value);
  return date ? WEEKDAYS[date.getDay()] : undefined;
}

function dayPart(value: string | undefined): string | undefined {
  if (!value) return undefined;
  const match = value.match(/T(\d{2}):/u) ?? value.match(/\b(\d{2}):/u);
  const hour = Number(match?.[1]);
  if (!Number.isInteger(hour)) return undefined;
  if (hour < 6) return "ночь";
  if (hour < 12) return "утро";
  if (hour < 18) return "день";
  return "вечер";
}

function ranked(
  values: Array<{ value?: string | undefined; observedAt?: string | undefined }>,
  limit = 8,
): RankedPreference[] {
  const scores = new Map<string, { value: string; evidenceCount: number; lastObservedAt?: string }>();
  for (const item of values) {
    const value = item.value?.trim();
    if (!value) continue;
    const key = value.toLocaleLowerCase("ru");
    const current = scores.get(key) ?? { value, evidenceCount: 0 };
    current.evidenceCount += 1;
    if (item.observedAt && (!current.lastObservedAt || item.observedAt > current.lastObservedAt)) {
      current.lastObservedAt = item.observedAt;
    }
    scores.set(key, current);
  }
  return [...scores.values()]
    .sort((left, right) =>
      right.evidenceCount - left.evidenceCount ||
      String(right.lastObservedAt ?? "").localeCompare(String(left.lastObservedAt ?? "")) ||
      left.value.localeCompare(right.value, "ru"),
    )
    .slice(0, limit);
}

function eventKind(order: OrderSignal): string | undefined {
  const text = `${order.objectType} ${order.title} ${order.eventName}`.toLocaleLowerCase("ru");
  if (/concert|концерт|festival|фестивал/u.test(text)) return "концерты";
  if (/theatre|spectacle|театр|спектак|мюзикл/u.test(text)) return "театр";
  if (/movie|cinema|кино|фильм/u.test(text)) return "кино";
  if (/museum|exhibition|музе|выстав/u.test(text)) return "выставки и музеи";
  if (/stand.?up|стендап/u.test(text)) return "стендап";
  return undefined;
}

function travelKind(order: OrderSignal): "flight" | "train" | "hotel" | undefined {
  const text = `${order.objectType} ${order.title}`.toLocaleLowerCase("ru");
  if (/avia|flight|авиа|перел[её]т/u.test(text)) return "flight";
  if (/train|trains_ticket|поезд|жд/u.test(text)) return "train";
  if (/hotel|отел|гостиниц/u.test(text)) return "hotel";
  return undefined;
}

export function emptyBehavioralInsights(): BehavioralInsights {
  return {
    audience: { ageBand: "unknown", adultContentAllowed: null, source: "unknown" },
    events: {
      purchaseCount: 0,
      kindAffinities: [],
      genreAffinities: [],
      venueAffinities: [],
      preferredWeekdays: [],
      preferredDayParts: [],
      averageOrderRub: 0,
      medianOrderRub: 0,
      averagePartySize: 0,
    },
    leisureSpending: {
      transactionCount: 0,
      monthlySpendRub: 0,
      averageCheckRub: 0,
      medianCheckRub: 0,
      preferredWeekdays: [],
      preferredDayParts: [],
    },
    travel: {
      orderCount: 0,
      flightOrderCount: 0,
      trainOrderCount: 0,
      hotelOrderCount: 0,
      averageOrderRub: 0,
      preferredHotelStars: [],
      preferredMealTypes: [],
      averageHotelNights: 0,
      averageHotelGuests: 0,
    },
  };
}

export function buildBehavioralInsights(input: {
  operations: ProfileOperation[];
  orders: OrderSignal[];
  eventDetails: EventOrderDetailsData[];
  travelDetails: TravelOrderDetailsData[];
  audience?: AudienceProfileData;
  analysisWindowDays: number;
}): BehavioralInsights {
  const base = emptyBehavioralInsights();
  const acceptedOrders = input.orders.filter((order) => !REJECTED_STATUS.test(order.status));
  const eventOrders = acceptedOrders.filter((order) => Boolean(eventKind(order)));
  const travelOrders = acceptedOrders.filter((order) =>
    Boolean(travelKind(order)) || TRAVEL_PATTERN.test(`${order.objectType} ${order.title}`));
  const detailByOrder = new Map(input.eventDetails.map((detail) => [detail.orderId, detail]));
  const eventAmounts = eventOrders.map((order) =>
    numeric(detailByOrder.get(order.orderId)?.totalAmountRub) || numeric(order.amount)).filter(Boolean);
  const eventMoments = eventOrders.map((order) => ({
    order,
    detail: detailByOrder.get(order.orderId),
  }));
  const partySizes = input.eventDetails.map((detail) => detail.seatCount).filter((value) => value > 0);

  const leisureOperations = input.operations.filter((operation) => {
    const text = `${operation.category ?? ""} ${operation.description}`;
    return operation.type.toLocaleLowerCase("ru") === "debit" && LEISURE_PATTERN.test(text);
  });
  const leisureAmounts = leisureOperations.map((operation) => numeric(operation.amount)).filter(Boolean);
  const leisureSpend = leisureAmounts.reduce((sum, value) => sum + value, 0);

  const travelDetailsAvailable = input.travelDetails.filter((detail) => detail.detailsAvailable);
  const hotelNights = travelDetailsAvailable.flatMap((detail) => {
    const start = validDate(detail.checkInDate);
    const end = validDate(detail.checkOutDate);
    if (!start || !end || end <= start) return [];
    return [Math.round((end.getTime() - start.getTime()) / 86_400_000)];
  });
  const hotelGuests = travelDetailsAvailable.map((detail) => detail.guestCount ?? 0).filter((value) => value > 0);
  const travelAmounts = travelOrders.map((order) => numeric(order.amount)).filter(Boolean);

  return {
    audience: input.audience
      ? { ...input.audience, source: input.audience.ageBand === "unknown" ? "unknown" : "bank" }
      : base.audience,
    events: {
      purchaseCount: eventOrders.length,
      kindAffinities: ranked(eventOrders.map((order) => ({
        value: eventKind(order), observedAt: order.createdAt,
      }))),
      genreAffinities: ranked(eventMoments.flatMap(({ order, detail }) =>
        (detail?.genres ?? []).map((value) => ({ value, observedAt: order.createdAt })))),
      venueAffinities: ranked(eventMoments.map(({ order, detail }) => ({
        value: detail?.venue, observedAt: order.createdAt,
      }))),
      preferredWeekdays: ranked(eventMoments.map(({ order, detail }) => ({
        value: weekday(detail?.startDateTime), observedAt: order.createdAt,
      }))),
      preferredDayParts: ranked(eventMoments.map(({ order, detail }) => ({
        value: dayPart(detail?.startDateTime), observedAt: order.createdAt,
      }))),
      averageOrderRub: round(average(eventAmounts)),
      medianOrderRub: round(median(eventAmounts)),
      averagePartySize: Math.round(average(partySizes) * 10) / 10,
    },
    leisureSpending: {
      transactionCount: leisureOperations.length,
      monthlySpendRub: round(leisureSpend * 30 / Math.max(1, input.analysisWindowDays)),
      averageCheckRub: round(average(leisureAmounts)),
      medianCheckRub: round(median(leisureAmounts)),
      preferredWeekdays: ranked(leisureOperations.map((operation) => ({
        value: weekday(operation.occurredAt), observedAt: operation.occurredAt,
      }))),
      preferredDayParts: ranked(leisureOperations.map((operation) => ({
        value: dayPart(operation.occurredAt), observedAt: operation.occurredAt,
      }))),
    },
    travel: {
      orderCount: travelOrders.length,
      flightOrderCount: travelOrders.filter((order) => travelKind(order) === "flight").length,
      trainOrderCount: travelOrders.filter((order) => travelKind(order) === "train").length,
      hotelOrderCount: travelOrders.filter((order) => travelKind(order) === "hotel").length,
      averageOrderRub: round(average(travelAmounts)),
      preferredHotelStars: ranked(travelDetailsAvailable.map((detail) => ({
        value: detail.hotelStars ? `${detail.hotelStars}★` : undefined,
        observedAt: detail.createdAt,
      }))),
      preferredMealTypes: ranked(travelDetailsAvailable.flatMap((detail) =>
        (detail.mealTypes ?? []).map((value) => ({ value, observedAt: detail.createdAt })))),
      averageHotelNights: Math.round(average(hotelNights) * 10) / 10,
      averageHotelGuests: Math.round(average(hotelGuests) * 10) / 10,
    },
  };
}
