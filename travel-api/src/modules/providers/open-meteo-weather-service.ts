import type {
  City,
  ClimateWeatherDay,
  ForecastWeatherDay,
  WeatherDay,
  WeatherReport,
} from "@travel-growth-inspiration/contracts";

import type { DateWindow } from "./provider-types.js";

const DAY_MS = 86_400_000;
const FORECAST_DAYS = 16;
const FORECAST_TTL_MS = 60 * 60_000;
const CLIMATE_START_DATE = "1991-01-01";
const CLIMATE_END_DATE = "2020-12-31";
const PRECIPITATION_DAY_THRESHOLD_MM = 1;

type HistoricalDay = {
  date: string;
  temperatureMinC: number;
  temperatureMaxC: number;
  precipitationMm: number;
};

type ForecastCacheEntry = {
  expiresAt: number;
  days: Map<string, ForecastWeatherDay>;
};

type OpenMeteoDaily = {
  time?: unknown;
  temperature_2m_min?: unknown;
  temperature_2m_max?: unknown;
  precipitation_probability_max?: unknown;
  precipitation_sum?: unknown;
  weather_code?: unknown;
};

type OpenMeteoResponse = {
  daily?: OpenMeteoDaily;
  error?: boolean;
  reason?: string;
};

export type WeatherLookupResult = {
  data: WeatherReport;
  warnings: string[];
  available: boolean;
  source: string;
  checkedAt: string;
};

export interface WeatherService {
  forTrip(city: City, window: DateWindow): Promise<WeatherLookupResult>;
}

export class UnavailableWeatherService implements WeatherService {
  async forTrip(): Promise<WeatherLookupResult> {
    return {
      data: { days: [] },
      warnings: [],
      available: false,
      source: "Open-Meteo",
      checkedAt: new Date().toISOString(),
    };
  }
}

export type OpenMeteoWeatherOptions = {
  forecastUrl?: string;
  archiveUrl?: string;
  timeoutMs?: number;
  forecastTtlMs?: number;
  fetcher?: typeof fetch;
  now?: () => Date;
};

function addDays(date: string, days: number): string {
  return new Date(Date.parse(`${date}T12:00:00.000Z`) + days * DAY_MS).toISOString().slice(0, 10);
}

function datesInWindow(window: DateWindow): string[] {
  const dates: string[] = [];
  for (let date = window.startDate; date <= window.endDate; date = addDays(date, 1)) {
    dates.push(date);
  }
  return dates;
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

function numbers(value: unknown): Array<number | undefined> {
  if (!Array.isArray(value)) return [];
  return value.map((item) => {
    if (item === null || item === undefined || typeof item === "boolean" || item === "") return undefined;
    const number = typeof item === "number" ? item : Number(item);
    return Number.isFinite(number) ? number : undefined;
  });
}

function average(values: number[]): number {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function climateMonthDays(date: string): Set<string> {
  const anchor = new Date(`${date.slice(0, 4)}-${date.slice(5)}T12:00:00.000Z`);
  anchor.setUTCFullYear(2000);
  return new Set(
    Array.from({ length: 7 }, (_, index) => {
      const sample = new Date(anchor);
      sample.setUTCDate(sample.getUTCDate() + index - 3);
      return sample.toISOString().slice(5, 10);
    }),
  );
}

export class OpenMeteoWeatherService implements WeatherService {
  readonly #forecastUrl: string;
  readonly #archiveUrl: string;
  readonly #timeoutMs: number;
  readonly #forecastTtlMs: number;
  readonly #fetcher: typeof fetch;
  readonly #now: () => Date;
  readonly #forecastCache = new Map<string, ForecastCacheEntry>();
  readonly #forecastInflight = new Map<string, Promise<Map<string, ForecastWeatherDay>>>();
  readonly #climateCache = new Map<string, HistoricalDay[]>();
  readonly #climateInflight = new Map<string, Promise<HistoricalDay[]>>();

  constructor(options: OpenMeteoWeatherOptions = {}) {
    this.#forecastUrl = options.forecastUrl ?? "https://api.open-meteo.com/v1/forecast";
    this.#archiveUrl = options.archiveUrl ?? "https://archive-api.open-meteo.com/v1/archive";
    this.#timeoutMs = options.timeoutMs ?? 15_000;
    this.#forecastTtlMs = options.forecastTtlMs ?? FORECAST_TTL_MS;
    this.#fetcher = options.fetcher ?? globalThis.fetch;
    this.#now = options.now ?? (() => new Date());
  }

  async forTrip(city: City, window: DateWindow): Promise<WeatherLookupResult> {
    const tripDates = datesInWindow(window);
    const today = this.#now().toISOString().slice(0, 10);
    const lastForecastDate = addDays(today, FORECAST_DAYS - 1);
    const isForecastDate = (date: string) => date >= today && date <= lastForecastDate;
    const needsForecast = tripDates.some(isForecastDate);
    const needsClimate = tripDates.some((date) => !isForecastDate(date));
    const warnings: string[] = [];

    let forecast = new Map<string, ForecastWeatherDay>();
    let history: HistoricalDay[] | undefined;
    const [forecastResult, climateResult] = await Promise.allSettled([
      needsForecast ? this.#forecast(city) : Promise.resolve(forecast),
      needsClimate ? this.#history(city) : Promise.resolve(undefined),
    ]);
    if (forecastResult.status === "fulfilled") {
      forecast = forecastResult.value;
    } else {
      warnings.push(`Прогноз погоды для ${city.name} недоступен: ${this.#message(forecastResult.reason)}`);
    }
    if (climateResult.status === "fulfilled") {
      history = climateResult.value;
    } else {
      warnings.push(`Погодная статистика для ${city.name} недоступна: ${this.#message(climateResult.reason)}`);
    }

    const missingForecast = tripDates.some((date) => isForecastDate(date) && !forecast.has(date));
    if (missingForecast && !history && !needsClimate) {
      try {
        history = await this.#history(city);
      } catch (error) {
        warnings.push(`Погодная статистика для ${city.name} недоступна: ${this.#message(error)}`);
      }
    }

    const days: WeatherDay[] = [];
    for (const date of tripDates) {
      const forecastDay = isForecastDate(date) ? forecast.get(date) : undefined;
      if (forecastDay) {
        days.push(forecastDay);
        continue;
      }
      const climateDay = history ? this.#climateDay(date, history) : undefined;
      if (climateDay) days.push(climateDay);
    }
    if (days.length < tripDates.length) {
      warnings.push(`Погода доступна для ${days.length} из ${tripDates.length} дней поездки.`);
    }
    const kinds = new Set(days.map((day) => day.kind));
    const source = kinds.size > 1
      ? "Open-Meteo Forecast + ERA5"
      : kinds.has("forecast")
        ? "Open-Meteo Forecast"
        : kinds.has("climate")
          ? "Open-Meteo ERA5"
          : "Open-Meteo";
    return {
      data: { days },
      warnings: [...new Set(warnings)],
      available: days.length > 0,
      source,
      checkedAt: this.#now().toISOString(),
    };
  }

  async #forecast(city: City): Promise<Map<string, ForecastWeatherDay>> {
    const key = this.#key(city);
    const cached = this.#forecastCache.get(key);
    const now = this.#now().getTime();
    if (cached && cached.expiresAt > now) return cached.days;
    const inflight = this.#forecastInflight.get(key);
    if (inflight) return inflight;
    const request = this.#loadForecast(city)
      .then((days) => {
        this.#forecastCache.set(key, { days, expiresAt: this.#now().getTime() + this.#forecastTtlMs });
        return days;
      })
      .finally(() => this.#forecastInflight.delete(key));
    this.#forecastInflight.set(key, request);
    return request;
  }

  async #history(city: City): Promise<HistoricalDay[]> {
    const key = this.#key(city);
    const cached = this.#climateCache.get(key);
    if (cached) return cached;
    const inflight = this.#climateInflight.get(key);
    if (inflight) return inflight;
    const request = this.#loadHistory(city)
      .then((days) => {
        this.#climateCache.set(key, days);
        return days;
      })
      .finally(() => this.#climateInflight.delete(key));
    this.#climateInflight.set(key, request);
    return request;
  }

  async #loadForecast(city: City): Promise<Map<string, ForecastWeatherDay>> {
    const url = new URL(this.#forecastUrl);
    url.searchParams.set("latitude", String(city.latitude));
    url.searchParams.set("longitude", String(city.longitude));
    url.searchParams.set(
      "daily",
      "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
    );
    url.searchParams.set("forecast_days", String(FORECAST_DAYS));
    url.searchParams.set("timezone", "auto");
    const payload = await this.#json(url);
    const dates = strings(payload.daily?.time);
    const minimums = numbers(payload.daily?.temperature_2m_min);
    const maximums = numbers(payload.daily?.temperature_2m_max);
    const probabilities = numbers(payload.daily?.precipitation_probability_max);
    const weatherCodes = numbers(payload.daily?.weather_code);
    const days = new Map<string, ForecastWeatherDay>();
    for (const [index, date] of dates.entries()) {
      const minimum = minimums[index];
      const maximum = maximums[index];
      const probability = probabilities[index];
      const weatherCode = weatherCodes[index];
      if (minimum === undefined || maximum === undefined || probability === undefined || weatherCode === undefined) continue;
      days.set(date, {
        date,
        kind: "forecast",
        temperatureMinC: Math.round(minimum),
        temperatureMaxC: Math.round(maximum),
        precipitationProbabilityPct: Math.max(0, Math.min(100, Math.round(probability))),
        weatherCode: Math.max(0, Math.round(weatherCode)),
      });
    }
    if (days.size === 0) throw new Error("источник не вернул дневной прогноз");
    return days;
  }

  async #loadHistory(city: City): Promise<HistoricalDay[]> {
    const url = new URL(this.#archiveUrl);
    url.searchParams.set("latitude", String(city.latitude));
    url.searchParams.set("longitude", String(city.longitude));
    url.searchParams.set("start_date", CLIMATE_START_DATE);
    url.searchParams.set("end_date", CLIMATE_END_DATE);
    url.searchParams.set("daily", "temperature_2m_max,temperature_2m_min,precipitation_sum");
    url.searchParams.set("models", "era5");
    url.searchParams.set("timezone", "auto");
    const payload = await this.#json(url);
    const dates = strings(payload.daily?.time);
    const minimums = numbers(payload.daily?.temperature_2m_min);
    const maximums = numbers(payload.daily?.temperature_2m_max);
    const precipitation = numbers(payload.daily?.precipitation_sum);
    const days: HistoricalDay[] = [];
    for (const [index, date] of dates.entries()) {
      const minimum = minimums[index];
      const maximum = maximums[index];
      const precipitationMm = precipitation[index];
      if (minimum === undefined || maximum === undefined || precipitationMm === undefined) continue;
      days.push({ date, temperatureMinC: minimum, temperatureMaxC: maximum, precipitationMm });
    }
    if (days.length === 0) throw new Error("источник не вернул исторические данные");
    return days;
  }

  #climateDay(date: string, history: HistoricalDay[]): ClimateWeatherDay | undefined {
    const monthDays = climateMonthDays(date);
    const samples = history.filter((day) => monthDays.has(day.date.slice(5, 10)));
    if (samples.length === 0) return undefined;
    return {
      date,
      kind: "climate",
      temperatureMinC: Math.round(average(samples.map((sample) => sample.temperatureMinC))),
      temperatureMaxC: Math.round(average(samples.map((sample) => sample.temperatureMaxC))),
      precipitationFrequencyPct: Math.round(
        samples.filter((sample) => sample.precipitationMm >= PRECIPITATION_DAY_THRESHOLD_MM).length /
          samples.length * 100,
      ),
      sampleSize: samples.length,
    };
  }

  async #json(url: URL): Promise<OpenMeteoResponse> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.#timeoutMs);
    try {
      const response = await this.#fetcher(url, { signal: controller.signal });
      const payload = await response.json() as OpenMeteoResponse;
      if (!response.ok || payload.error) {
        throw new Error(payload.reason ?? `HTTP ${response.status}`);
      }
      return payload;
    } finally {
      clearTimeout(timeout);
    }
  }

  #key(city: City): string {
    return `${city.id}:${city.latitude.toFixed(4)}:${city.longitude.toFixed(4)}`;
  }

  #message(error: unknown): string {
    if (error instanceof Error && error.name === "AbortError") return "истекло время ожидания";
    return error instanceof Error ? error.message : "неизвестная ошибка";
  }
}
