import type { City } from "@travel-growth-inspiration/contracts";

import { OsmNearbyClient } from "./osm-nearby-client.js";
import type {
  NearbyAnchor,
  NearbyPlace,
  NearbyPlacesProvider,
  NearbySearchOptions,
  ProviderResult,
} from "./provider-types.js";

type TwoGisWorkingHours = {
  from?: string | null;
  to?: string | null;
};

type TwoGisSchedule = Partial<Record<DayKey, {
  working_hours?: TwoGisWorkingHours[];
}>> & {
  is_24x7?: boolean;
  comment?: string;
  description?: string;
};

type TwoGisItem = {
  id?: string;
  name?: string;
  type?: string;
  address_name?: string;
  full_address_name?: string;
  city_alias?: string;
  point?: { lat?: number; lon?: number };
  rubrics?: Array<{ name?: string }>;
  reviews?: {
    general_rating?: number;
    general_review_count?: number;
    rating?: number;
    review_count?: number;
  };
  schedule?: TwoGisSchedule;
  attribute_groups?: Array<{
    attributes?: Array<{ name?: string; tag?: string }>;
  }>;
  delivery?: unknown;
};

type TwoGisPayload = {
  meta?: {
    code?: number;
    error?: { message?: string };
  };
  result?: { items?: TwoGisItem[] };
};

const NEARBY_RADIUS_METERS = 1_800;
const DAY_KEYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] as const;
type DayKey = typeof DAY_KEYS[number];
const DAY_LABELS: Record<DayKey, string> = {
  Mon: "Пн",
  Tue: "Вт",
  Wed: "Ср",
  Thu: "Чт",
  Fri: "Пт",
  Sat: "Сб",
  Sun: "Вс",
};

function unique(values: Array<string | undefined>): string[] {
  return [...new Set(values.map((value) => value?.trim()).filter((value): value is string => Boolean(value)))];
}

function finite(value: unknown): number | undefined {
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function distanceMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const radius = 6_371_000;
  const toRadians = (degrees: number) => (degrees * Math.PI) / 180;
  const deltaLatitude = toRadians(lat2 - lat1);
  const deltaLongitude = toRadians(lon2 - lon1);
  const a =
    Math.sin(deltaLatitude / 2) ** 2 +
    Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) * Math.sin(deltaLongitude / 2) ** 2;
  return Math.round(radius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
}

function scheduleText(schedule: TwoGisSchedule | undefined): string | undefined {
  if (!schedule) return undefined;
  if (schedule.is_24x7) return "Круглосуточно";
  const days = DAY_KEYS.map((day) => {
    const hours = schedule[day]?.working_hours ?? [];
    const value = hours
      .map(({ from, to }) => from && to ? `${from}–${to}` : undefined)
      .filter((item): item is string => Boolean(item))
      .join(", ");
    return { day, value };
  });
  const groups: Array<{ first: DayKey; last: DayKey; value: string }> = [];
  for (const item of days) {
    if (!item.value) continue;
    const previous = groups.at(-1);
    const previousIndex = previous ? DAY_KEYS.indexOf(previous.last) : -2;
    const currentIndex = DAY_KEYS.indexOf(item.day);
    if (previous && previous.value === item.value && currentIndex === previousIndex + 1) {
      previous.last = item.day;
    } else {
      groups.push({ first: item.day, last: item.day, value: item.value });
    }
  }
  if (groups.length) {
    return groups
      .map(({ first, last, value }) =>
        `${DAY_LABELS[first]}${first === last ? "" : `–${DAY_LABELS[last]}`} ${value}`)
      .join("; ");
  }
  return schedule.description?.trim() || schedule.comment?.trim() || undefined;
}

function sourceUrl(item: TwoGisItem, city: City): string | undefined {
  const id = item.id?.split("_")[0]?.trim();
  const cityAlias = item.city_alias?.trim() || city.id;
  if (!id || !/^[0-9]+$/u.test(id) || !/^[a-z0-9-]+$/u.test(cityAlias)) return undefined;
  return `https://2gis.ru/${cityAlias}/firm/${id}`;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export class TwoGisNearbyClient implements NearbyPlacesProvider {
  readonly #url: string;
  readonly #apiKey: string;
  readonly #timeoutMs: number;

  constructor(url: string, apiKey: string, timeoutMs: number) {
    this.#url = url;
    this.#apiKey = apiKey;
    this.#timeoutMs = timeoutMs;
  }

  async nearby(
    city: City,
    anchor: NearbyAnchor,
    _options: NearbySearchOptions = {},
  ): Promise<ProviderResult<NearbyPlace[]>> {
    const checkedAt = new Date().toISOString();
    if (anchor.latitude === undefined || anchor.longitude === undefined) {
      return {
        data: [],
        warnings: [`Для поиска 2ГИС не определены координаты «${anchor.name}».`],
        isFallback: false,
        source: "2ГИС",
        checkedAt,
      };
    }
    const url = new URL(this.#url);
    url.searchParams.set("key", this.#apiKey);
    url.searchParams.set("locale", "ru_RU");
    url.searchParams.set("q", "рестораны");
    url.searchParams.set("point", `${anchor.longitude},${anchor.latitude}`);
    url.searchParams.set("radius", String(NEARBY_RADIUS_METERS));
    // Demo keys are capped at 10 results per page by the current Places API.
    url.searchParams.set("page_size", "10");
    url.searchParams.set("sort", "distance");
    url.searchParams.set("search_nearby", "true");
    url.searchParams.set("search_input_method", "software_generated");
    url.searchParams.set(
      "fields",
      [
        "items.point",
        "items.full_address_name",
        "items.rubrics",
        "items.brand",
        "items.schedule",
        "items.reviews",
        "items.attribute_groups",
        "items.delivery",
        "items.dates.updated_at",
      ].join(","),
    );
    const response = await fetch(url, {
      headers: {
        accept: "application/json",
        "user-agent": "TravelNova/0.1 local-alpha",
      },
      signal: AbortSignal.timeout(this.#timeoutMs),
    });
    if (!response.ok) throw new Error(`2ГИС ответил с кодом ${response.status}`);
    const payload = (await response.json()) as TwoGisPayload;
    if (payload.meta?.code !== undefined && payload.meta.code !== 200) {
      throw new Error(payload.meta.error?.message || `2ГИС вернул код ${payload.meta.code}`);
    }
    const places = (payload.result?.items ?? [])
      .map((item): NearbyPlace | undefined => {
        const id = item.id?.split("_")[0]?.trim();
        const latitude = finite(item.point?.lat);
        const longitude = finite(item.point?.lon);
        const name = item.name?.trim();
        if (!id || !name || latitude === undefined || longitude === undefined) return undefined;
        const distance = distanceMeters(anchor.latitude!, anchor.longitude!, latitude, longitude);
        if (distance > NEARBY_RADIUS_METERS) return undefined;
        const rawAttributes = unique(
          (item.attribute_groups ?? []).flatMap((group) =>
            (group.attributes ?? []).map((attribute) => attribute.name)),
        );
        const cuisines = rawAttributes.filter((value) => /кухн/u.test(value.toLocaleLowerCase("ru")));
        const averageCheck = rawAttributes.find((value) =>
          /средн.*чек|чек.*(?:₽|руб)/u.test(value.toLocaleLowerCase("ru")));
        const attributes = rawAttributes
          .filter((value) => value !== averageCheck && !cuisines.includes(value) && value.length <= 80)
          .slice(0, 5);
        const rating = finite(item.reviews?.general_rating ?? item.reviews?.rating);
        const reviewCount = finite(
          item.reviews?.general_review_count ?? item.reviews?.review_count,
        );
        const openingHours = scheduleText(item.schedule);
        const itemSourceUrl = sourceUrl(item, city);
        return {
          osmId: `2gis/${id}`,
          type: "restaurant",
          name,
          latitude,
          longitude,
          ...(cuisines.length ? { cuisine: cuisines.join(", ") } : {}),
          ...(openingHours ? { openingHours } : {}),
          ...(item.full_address_name || item.address_name
            ? { address: item.full_address_name || item.address_name }
            : {}),
          ...(rating !== undefined && rating >= 0 && rating <= 5 ? { rating } : {}),
          ...(reviewCount !== undefined && reviewCount >= 0
            ? { reviewCount: Math.round(reviewCount) }
            : {}),
          ...(averageCheck ? { averageCheck } : {}),
          ...(attributes.length ? { attributes } : {}),
          ...(Boolean(item.delivery) || rawAttributes.some((value) => /доставк/u.test(value.toLocaleLowerCase("ru")))
            ? { delivery: true }
            : {}),
          ...(itemSourceUrl ? { sourceUrl: itemSourceUrl } : {}),
          distanceMeters: distance,
          source: "2ГИС",
          checkedAt,
        };
      })
      .filter((place): place is NearbyPlace => Boolean(place))
      .sort((left, right) => left.distanceMeters - right.distanceMeters)
      .slice(0, 15);
    return {
      data: places,
      warnings: [],
      isFallback: false,
      source: "2ГИС",
      checkedAt,
    };
  }
}

export class PreferredNearbyClient implements NearbyPlacesProvider {
  readonly #osm: OsmNearbyClient;
  readonly #preferred: NearbyPlacesProvider | undefined;

  constructor(osm: OsmNearbyClient, preferred?: NearbyPlacesProvider) {
    this.#osm = osm;
    this.#preferred = preferred;
  }

  async nearby(
    city: City,
    anchor: NearbyAnchor,
    options: NearbySearchOptions = {},
  ): Promise<ProviderResult<NearbyPlace[]>> {
    if (!this.#preferred) return this.#osm.nearby(city, anchor, options);
    const resolvedAnchor = await this.#osm.resolveAnchor(city, anchor);
    if (!resolvedAnchor) return this.#osm.nearby(city, anchor, options);

    const osmPromise = options.includePointsOfInterest
      ? this.#osm.nearby(city, resolvedAnchor, options)
      : undefined;
    let preferredResult: ProviderResult<NearbyPlace[]> | undefined;
    let preferredWarning: string | undefined;
    try {
      preferredResult = await this.#preferred.nearby(city, resolvedAnchor, options);
    } catch (error) {
      preferredWarning = `2ГИС временно недоступен (${errorMessage(error)}); использован OpenStreetMap.`;
    }

    if (preferredResult?.data.some((place) => place.type === "restaurant")) {
      if (!osmPromise) return preferredResult;
      try {
        const osmResult = await osmPromise;
        return {
          data: [
            ...preferredResult.data.filter((place) => place.type === "restaurant"),
            ...osmResult.data.filter((place) => place.type === "poi"),
          ],
          warnings: unique([...preferredResult.warnings, ...osmResult.warnings]),
          isFallback: false,
          source: osmResult.data.some((place) => place.type === "poi")
            ? "2ГИС + OpenStreetMap"
            : "2ГИС",
          checkedAt: [preferredResult.checkedAt, osmResult.checkedAt].sort().at(-1)!,
        };
      } catch (error) {
        return {
          ...preferredResult,
          warnings: [
            ...preferredResult.warnings,
            `Достопримечательности OpenStreetMap временно недоступны: ${errorMessage(error)}`,
          ],
        };
      }
    }

    const osmResult = await (osmPromise ?? this.#osm.nearby(city, resolvedAnchor, options));
    return {
      ...osmResult,
      warnings: unique([
        ...(preferredResult?.warnings ?? []),
        preferredWarning ?? "2ГИС не нашёл рестораны рядом; использован OpenStreetMap.",
        ...osmResult.warnings,
      ]),
      isFallback: true,
    };
  }
}
