import type { City, ImageAsset } from "@travel-growth-inspiration/contracts";

import type {
  NearbyAnchor,
  NearbyPlace,
  NearbySearchOptions,
  ProviderResult,
} from "./provider-types.js";

type OsmElement = {
  id: number;
  type: string;
  lat?: number;
  lon?: number;
  center?: { lat?: number; lon?: number };
  tags?: Record<string, string>;
};

type OsmPlaceCandidate = {
  place: NearbyPlace;
  wikimediaCommons?: string;
  wikipedia?: string;
};

type WikimediaFileResponse = {
  file_description_url?: string;
  preferred?: { url?: string };
  thumbnail?: { url?: string };
  original?: { url?: string };
};

type WikipediaSummaryResponse = {
  thumbnail?: { source?: string };
  originalimage?: { source?: string };
  content_urls?: { desktop?: { page?: string } };
};

type NominatimSearchResult = {
  osm_type?: string;
  osm_id?: number;
  lat?: string;
  lon?: string;
  category?: string;
  type?: string;
  name?: string;
  display_name?: string;
  extratags?: { cuisine?: string; opening_hours?: string };
};

const MAX_OVERPASS_CONCURRENCY = 2;
const NEARBY_RADIUS_METERS = 1_800;

function safeHttpsUrl(value: unknown, allowedHosts: Set<string>): string | undefined {
  if (typeof value !== "string" || !value.trim()) return undefined;
  try {
    const url = new URL(value.startsWith("//") ? `https:${value}` : value);
    if (url.protocol !== "https:" || !allowedHosts.has(url.hostname)) return undefined;
    return url.toString();
  } catch {
    return undefined;
  }
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

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/gu, "\\$&");
}

function normalizeAddress(address: string, cityName: string): string {
  const city = escapeRegExp(cityName);
  return address
    .replace(new RegExp(`(^|,\\s*)(?:г(?:ород)?\\.?\\s*)?${city}(?=,|$)`, "giu"), "$1")
    .replace(/(?:дом|д)\.?\s*(?=\d)/giu, "")
    .replace(/\s*,\s*/gu, ", ")
    .replace(/(?:^,\s*|,\s*$)/gu, "")
    .replace(/\s+/gu, " ")
    .trim();
}

function geocodingQueries(city: City, anchor: NearbyAnchor): string[] {
  const address = anchor.address ? normalizeAddress(anchor.address, city.name) : "";
  const venueName = anchor.name.split(",")[0]?.trim() ?? anchor.name.trim();
  return [...new Set([
    ...(address ? [`${address}, ${city.name}, Россия`] : []),
    ...(venueName ? [`${venueName}, ${city.name}, Россия`] : []),
  ])];
}

export class OsmNearbyClient {
  readonly #overpassUrl: string;
  readonly #nominatimUrl: string;
  readonly #timeoutMs: number;
  readonly #geocodeCache = new Map<string, { latitude: number; longitude: number } | null>();
  readonly #imageCache = new Map<string, Promise<ImageAsset | undefined>>();
  #geocodeQueue: Promise<void> = Promise.resolve();
  #lastGeocodeAt = 0;
  #activeOverpassRequests = 0;
  readonly #overpassWaiters: Array<() => void> = [];

  constructor(overpassUrl: string, nominatimUrl: string, timeoutMs: number) {
    this.#overpassUrl = overpassUrl;
    this.#nominatimUrl = nominatimUrl.replace(/\/$/, "");
    this.#timeoutMs = timeoutMs;
  }

  async resolveAnchor(city: City, anchor: NearbyAnchor): Promise<NearbyAnchor | undefined> {
    if (anchor.latitude !== undefined && anchor.longitude !== undefined) return anchor;
    for (const query of geocodingQueries(city, anchor)) {
      const coordinates = await this.#geocode(query);
      if (coordinates) return { ...anchor, ...coordinates };
    }
    return undefined;
  }

  async nearby(
    city: City,
    anchor: NearbyAnchor,
    options: NearbySearchOptions = {},
  ): Promise<ProviderResult<NearbyPlace[]>> {
    const checkedAt = new Date().toISOString();
    const warnings: string[] = [];
    const resolvedAnchor = await this.resolveAnchor(city, anchor);
    if (!resolvedAnchor) {
      return {
        data: [],
        warnings: [`Точные координаты «${anchor.name}» не найдены: поиск мест рядом не выполнялся.`],
        isFallback: false,
        source: "OpenStreetMap",
        checkedAt,
      };
    }
    const latitude = resolvedAnchor.latitude!;
    const longitude = resolvedAnchor.longitude!;

    try {
      const placeKinds = new Set(options.placeKinds?.length ? options.placeKinds : ["culture"]);
      const pointsQuery = options.includePointsOfInterest
        ? [
            ...(placeKinds.has("culture") ? [`
        nwr[tourism~"museum|attraction|gallery"](around:${NEARBY_RADIUS_METERS},${latitude},${longitude});
        nwr[historic](around:${NEARBY_RADIUS_METERS},${latitude},${longitude});`] : []),
            ...(placeKinds.has("nature") ? [`
        nwr[tourism="viewpoint"](around:${NEARBY_RADIUS_METERS},${latitude},${longitude});
        nwr[leisure~"park|nature_reserve|garden"](around:${NEARBY_RADIUS_METERS},${latitude},${longitude});
        nwr[natural~"beach|wood"](around:${NEARBY_RADIUS_METERS},${latitude},${longitude});`] : []),
            ...(placeKinds.has("nightlife") ? [`
        nwr[amenity~"bar|pub|nightclub|music_venue"](around:${NEARBY_RADIUS_METERS},${latitude},${longitude});`] : []),
          ].join("")
        : "";
      const query = `[out:json][timeout:12];(
        nwr[amenity~"restaurant|cafe|fast_food|food_court"](around:${NEARBY_RADIUS_METERS},${latitude},${longitude});${pointsQuery}
      );out center tags;`;
      let response: Response | undefined;
      await this.#withOverpassSlot(async () => {
        for (let attempt = 0; attempt < 2; attempt += 1) {
          response = await fetch(this.#overpassUrl, {
            method: "POST",
            headers: {
              "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
              "user-agent": "TravelNova/0.1 local-alpha",
            },
            body: `data=${encodeURIComponent(query)}`,
            signal: AbortSignal.timeout(this.#timeoutMs),
          });
          if (response.ok || (response.status < 500 && response.status !== 429)) break;
        }
      });
      if (!response?.ok) throw new Error(`Overpass responded ${response?.status ?? "without response"}`);
      const payload = (await response.json()) as { elements?: OsmElement[] };
      const candidates = (payload.elements ?? [])
        .map((element): OsmPlaceCandidate | undefined => {
          const tags = element.tags ?? {};
          const elementLatitude = element.lat ?? element.center?.lat;
          const elementLongitude = element.lon ?? element.center?.lon;
          const name = tags.name ?? tags["name:ru"];
          if (
            !name || elementLatitude === undefined || elementLongitude === undefined ||
            ["temporarily_closed", "closed", "disused"].includes(tags.status ?? "")
          ) {
            return undefined;
          }
          const isRestaurant = ["restaurant", "cafe", "fast_food", "food_court"].includes(
            tags.amenity ?? "",
          );
          return {
            place: {
              osmId: `${element.type}/${element.id}`,
              type: isRestaurant ? "restaurant" : "poi",
              name,
              latitude: elementLatitude,
              longitude: elementLongitude,
              ...(tags.cuisine ? { cuisine: tags.cuisine.replaceAll(";", ", ") } : {}),
              ...(!isRestaurant
                ? { category: tags.amenity ?? tags.tourism ?? tags.leisure ?? tags.natural ?? (tags.historic ? "historic" : "place") }
                : {}),
              ...(tags.opening_hours ? { openingHours: tags.opening_hours } : {}),
              distanceMeters: distanceMeters(
                latitude,
                longitude,
                elementLatitude,
                elementLongitude,
              ),
              source: "OpenStreetMap",
              checkedAt,
            },
            ...(tags.wikimedia_commons ? { wikimediaCommons: tags.wikimedia_commons } : {}),
            ...(tags.wikipedia ? { wikipedia: tags.wikipedia } : {}),
          };
        })
        .filter((candidate): candidate is OsmPlaceCandidate => Boolean(candidate))
        .sort((left, right) => left.place.distanceMeters - right.place.distanceMeters);
      const restaurants = candidates
        .filter((candidate) => candidate.place.type === "restaurant")
        .slice(0, 15)
        .map((candidate) => candidate.place);
      const pointCandidates = candidates
        .filter((candidate) => candidate.place.type === "poi")
        .slice(0, 6);
      const pointsOfInterest = await Promise.all(
        pointCandidates.map(async (candidate): Promise<NearbyPlace> => {
          const image = await this.#resolveImage(candidate.wikimediaCommons, candidate.wikipedia);
          return {
            ...candidate.place,
            ...(image ? { image } : {}),
          };
        }),
      );
      return {
        data: [...restaurants, ...pointsOfInterest],
        warnings,
        isFallback: false,
        source: "OpenStreetMap",
        checkedAt,
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : "неизвестная ошибка";
      const restaurants = await this.#nearbyRestaurantsFromNominatim(latitude, longitude, checkedAt);
      return {
        data: restaurants,
        warnings: [
          ...warnings,
          restaurants.length > 0
            ? `Основной каталог OpenStreetMap не ответил (${message}); рестораны найдены резервным поиском.`
            : `OpenStreetMap временно недоступен: ${message}`,
        ],
        isFallback: restaurants.length > 0,
        source: "OpenStreetMap",
        checkedAt,
      };
    }
  }

  #resolveImage(
    wikimediaCommons: string | undefined,
    wikipedia: string | undefined,
  ): Promise<ImageAsset | undefined> {
    const commonsTitle = String(wikimediaCommons ?? "").trim();
    if (/^File:/iu.test(commonsTitle)) {
      return this.#cachedImage(`commons:${commonsTitle}`, () => this.#commonsImage(commonsTitle));
    }

    const match = String(wikipedia ?? "").trim().match(/^([a-z]{2,3}):(.+)$/iu);
    if (!match) return Promise.resolve(undefined);
    const language = match[1]!.toLowerCase();
    const title = match[2]!.trim();
    if (!title) return Promise.resolve(undefined);
    return this.#cachedImage(`wikipedia:${language}:${title}`, () =>
      this.#wikipediaImage(language, title),
    );
  }

  #cachedImage(
    key: string,
    loader: () => Promise<ImageAsset | undefined>,
  ): Promise<ImageAsset | undefined> {
    const cached = this.#imageCache.get(key);
    if (cached) return cached;
    const pending = loader().catch(() => undefined);
    this.#imageCache.set(key, pending);
    return pending;
  }

  async #commonsImage(title: string): Promise<ImageAsset | undefined> {
    try {
      const response = await fetch(
        `https://commons.wikimedia.org/w/rest.php/v1/file/${encodeURIComponent(title)}`,
        {
          headers: {
            accept: "application/json",
            "user-agent": "TravelNova/0.1 local-alpha",
          },
          signal: AbortSignal.timeout(this.#timeoutMs),
        },
      );
      if (!response.ok) return undefined;
      const payload = (await response.json()) as WikimediaFileResponse;
      const imageUrl = safeHttpsUrl(
        payload.preferred?.url ?? payload.thumbnail?.url ?? payload.original?.url,
        new Set(["upload.wikimedia.org"]),
      );
      if (!imageUrl) return undefined;
      const sourceUrl = safeHttpsUrl(
        payload.file_description_url,
        new Set(["commons.wikimedia.org"]),
      );
      return {
        url: imageUrl,
        source: "Wikimedia Commons",
        ...(sourceUrl ? { sourceUrl } : {}),
      };
    } catch {
      return undefined;
    }
  }

  async #wikipediaImage(language: string, title: string): Promise<ImageAsset | undefined> {
    const hostname = `${language}.wikipedia.org`;
    try {
      const response = await fetch(
        `https://${hostname}/api/rest_v1/page/summary/${encodeURIComponent(title.replaceAll(" ", "_"))}`,
        {
          headers: {
            accept: "application/json",
            "user-agent": "TravelNova/0.1 local-alpha",
          },
          signal: AbortSignal.timeout(this.#timeoutMs),
        },
      );
      if (!response.ok) return undefined;
      const payload = (await response.json()) as WikipediaSummaryResponse;
      const imageUrl = safeHttpsUrl(
        payload.thumbnail?.source ?? payload.originalimage?.source,
        new Set(["upload.wikimedia.org"]),
      );
      if (!imageUrl) return undefined;
      const sourceUrl = safeHttpsUrl(
        payload.content_urls?.desktop?.page,
        new Set([hostname]),
      );
      return {
        url: imageUrl,
        source: "Wikipedia",
        ...(sourceUrl ? { sourceUrl } : {}),
      };
    } catch {
      return undefined;
    }
  }

  async #geocode(query: string): Promise<{ latitude: number; longitude: number } | undefined> {
    if (this.#geocodeCache.has(query)) return this.#geocodeCache.get(query) ?? undefined;
    const payload = await this.#nominatimJson<NominatimSearchResult[]>((url) => {
      url.pathname = `${url.pathname}/search`.replace(/\/+/gu, "/");
      url.searchParams.set("q", query);
      url.searchParams.set("format", "jsonv2");
      url.searchParams.set("limit", "1");
    });
    const first = payload?.[0];
    const coordinates = first?.lat && first.lon
      ? { latitude: Number(first.lat), longitude: Number(first.lon) }
      : undefined;
    if (
      !coordinates ||
      !Number.isFinite(coordinates.latitude) ||
      !Number.isFinite(coordinates.longitude)
    ) {
      this.#geocodeCache.set(query, null);
      return undefined;
    }
    this.#geocodeCache.set(query, coordinates);
    return coordinates;
  }

  async #nearbyRestaurantsFromNominatim(
    latitude: number,
    longitude: number,
    checkedAt: string,
  ): Promise<NearbyPlace[]> {
    const latitudeDelta = NEARBY_RADIUS_METERS / 111_320;
    const longitudeDelta = NEARBY_RADIUS_METERS /
      Math.max(1, 111_320 * Math.cos((latitude * Math.PI) / 180));
    const results: NominatimSearchResult[] = [];
    for (const query of ["ресторан", "кафе"]) {
      const payload = await this.#nominatimJson<NominatimSearchResult[]>((url) => {
        url.pathname = `${url.pathname}/search`.replace(/\/+/gu, "/");
        url.searchParams.set("q", query);
        url.searchParams.set("format", "jsonv2");
        url.searchParams.set("limit", "6");
        url.searchParams.set("bounded", "1");
        url.searchParams.set(
          "viewbox",
          [
            longitude - longitudeDelta,
            latitude + latitudeDelta,
            longitude + longitudeDelta,
            latitude - latitudeDelta,
          ].join(","),
        );
        url.searchParams.set("extratags", "1");
      });
      results.push(...(payload ?? []));
      if (results.length >= 3) break;
    }
    return [...new Map(results.map((item) => [`${item.osm_type}/${item.osm_id}`, item])).values()]
      .map((item): NearbyPlace | undefined => {
        const itemLatitude = Number(item.lat);
        const itemLongitude = Number(item.lon);
        const name = item.name || item.display_name?.split(",")[0]?.trim();
        if (
          !item.osm_type || item.osm_id === undefined || !name ||
          !Number.isFinite(itemLatitude) || !Number.isFinite(itemLongitude) ||
          item.category !== "amenity" ||
          !["restaurant", "cafe", "fast_food", "food_court"].includes(item.type ?? "")
        ) return undefined;
        const distance = distanceMeters(latitude, longitude, itemLatitude, itemLongitude);
        if (distance > NEARBY_RADIUS_METERS) return undefined;
        return {
          osmId: `${item.osm_type}/${item.osm_id}`,
          type: "restaurant",
          name,
          latitude: itemLatitude,
          longitude: itemLongitude,
          ...(item.extratags?.cuisine
            ? { cuisine: item.extratags.cuisine.replaceAll(";", ", ") }
            : {}),
          ...(item.extratags?.opening_hours
            ? { openingHours: item.extratags.opening_hours }
            : {}),
          distanceMeters: distance,
          source: "OpenStreetMap",
          checkedAt,
        };
      })
      .filter((place): place is NearbyPlace => Boolean(place))
      .sort((left, right) => left.distanceMeters - right.distanceMeters)
      .slice(0, 3);
  }

  async #nominatimJson<T>(configure: (url: URL) => void): Promise<T | undefined> {
    let release: (() => void) | undefined;
    const previous = this.#geocodeQueue;
    this.#geocodeQueue = new Promise<void>((resolve) => {
      release = resolve;
    });
    await previous;
    try {
      const delay = Math.max(0, 1_000 - (Date.now() - this.#lastGeocodeAt));
      if (delay) await new Promise((resolve) => setTimeout(resolve, delay));
      const url = new URL(this.#nominatimUrl);
      configure(url);
      const response = await fetch(url, {
        headers: {
          accept: "application/json",
          "accept-language": "ru",
          "user-agent": "TravelNova/0.1 local-alpha",
        },
        signal: AbortSignal.timeout(this.#timeoutMs),
      });
      if (!response.ok) return undefined;
      return (await response.json()) as T;
    } catch {
      return undefined;
    } finally {
      this.#lastGeocodeAt = Date.now();
      release?.();
    }
  }

  async #withOverpassSlot<T>(task: () => Promise<T>): Promise<T> {
    if (this.#activeOverpassRequests >= MAX_OVERPASS_CONCURRENCY) {
      await new Promise<void>((resolve) => this.#overpassWaiters.push(resolve));
    }
    this.#activeOverpassRequests += 1;
    try {
      return await task();
    } finally {
      this.#activeOverpassRequests -= 1;
      this.#overpassWaiters.shift()?.();
    }
  }
}
