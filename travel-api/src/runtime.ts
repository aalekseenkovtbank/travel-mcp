import "./config/tls.js";
import { env } from "./config/env.js";
import { existsSync } from "node:fs";
import type { SystemReadiness } from "@travel-growth-inspiration/contracts";
import {
  LlmProxyEditorialService,
  type EditorialService,
} from "./modules/editorial/editorial-service.js";
import { DemoPlannerProvider } from "./modules/providers/demo-planner-provider.js";
import { OsmNearbyClient } from "./modules/providers/osm-nearby-client.js";
import {
  OpenMeteoWeatherService,
  type WeatherService,
} from "./modules/providers/open-meteo-weather-service.js";
import { ResilientPlannerProvider } from "./modules/providers/resilient-planner-provider.js";
import { TbankMcpClient } from "./modules/providers/tbank-mcp-client.js";
import { TbankPlannerProvider } from "./modules/providers/tbank-planner-provider.js";
import {
  PreferredNearbyClient,
  TwoGisNearbyClient,
} from "./modules/providers/two-gis-nearby-client.js";
import type { PlannerDataProvider } from "./modules/providers/provider-types.js";
import { TravelPlannerAgent } from "./modules/planner/travel-planner-agent.js";
import {
  LlmProxyTripIntentInterpreter,
  type TripIntentInterpreter,
} from "./modules/planner/trip-intent-interpreter.js";
import { TravelStore } from "./modules/storage/travel-store.js";

export type AppRuntime = {
  store: TravelStore;
  provider: PlannerDataProvider;
  agent: TravelPlannerAgent;
  intentInterpreter: TripIntentInterpreter;
  readiness: () => SystemReadiness;
  close: () => Promise<void>;
};

export type RuntimeOptions = {
  databasePath?: string;
  mode?: "auto" | "live" | "demo";
  llmProxyApiKey?: string;
  llmProxyBaseUrl?: string;
  llmProxyModel?: string;
  /** @deprecated Use llmProxyApiKey. */
  openAiApiKey?: string;
  /** @deprecated Use llmProxyBaseUrl. */
  openAiBaseUrl?: string;
  /** @deprecated Use llmProxyModel. */
  openAiModel?: string;
  editorial?: EditorialService;
  intentInterpreter?: TripIntentInterpreter;
  weatherService?: WeatherService;
  twoGisApiKey?: string;
};

export function readableMcpError(error: string | undefined): string | undefined {
  if (!error) return undefined;
  if (/-32001|request timed out|timed out|timeout/iu.test(error)) {
    return "T-Bank MCP не ответил вовремя; реальный контур временно недоступен";
  }
  return error;
}

export function createRuntime(options: RuntimeOptions = {}): AppRuntime {
  const mode = options.mode ?? env.DATA_MODE;
  const store = new TravelStore(options.databasePath ?? env.DATABASE_PATH);
  const mcp = new TbankMcpClient(
    env.TBANK_MCP_COMMAND,
    env.PROVIDER_TIMEOUT_MS,
    env.MCP_MAX_CONCURRENCY,
    env.MCP_FLIGHT_MAX_CONCURRENCY,
    env.MCP_HOTEL_MAX_CONCURRENCY,
  );
  const osm = new OsmNearbyClient(env.OVERPASS_URL, env.NOMINATIM_URL, env.PROVIDER_TIMEOUT_MS);
  const twoGisApiKey = options.twoGisApiKey ?? env.TWOGIS_API_KEY;
  const nearby = new PreferredNearbyClient(
    osm,
    twoGisApiKey
      ? new TwoGisNearbyClient(env.TWOGIS_PLACES_URL, twoGisApiKey, env.PROVIDER_TIMEOUT_MS)
      : undefined,
  );
  const live = new TbankPlannerProvider(
    mcp,
    nearby,
    env.HOTEL_PROVIDER_TIMEOUT_MS,
    env.FLIGHT_PROVIDER_TIMEOUT_MS,
  );
  const demo = new DemoPlannerProvider();
  const provider = new ResilientPlannerProvider(live, demo, mode);
  const llmProxyApiKey = options.llmProxyApiKey ?? options.openAiApiKey ?? env.LLM_PROXY_API_KEY;
  const llmProxyBaseUrl = options.llmProxyBaseUrl ?? options.openAiBaseUrl ?? env.LLM_PROXY_BASE_URL;
  const llmProxyModel = options.llmProxyModel ?? options.openAiModel ?? env.LLM_PROXY_MODEL;
  const editorial = options.editorial ?? new LlmProxyEditorialService(
    llmProxyApiKey,
    llmProxyModel,
    Math.max(env.PROVIDER_TIMEOUT_MS, 30_000),
    llmProxyBaseUrl,
  );
  const weather = options.weatherService ?? new OpenMeteoWeatherService({
    forecastUrl: env.OPEN_METEO_FORECAST_URL,
    archiveUrl: env.OPEN_METEO_ARCHIVE_URL,
    timeoutMs: env.PROVIDER_TIMEOUT_MS,
  });
  const intentInterpreter = options.intentInterpreter ?? new LlmProxyTripIntentInterpreter({
    ...(llmProxyApiKey ? { apiKey: llmProxyApiKey } : {}),
    model: llmProxyModel,
    timeoutMs: Math.max(env.PROVIDER_TIMEOUT_MS, 30_000),
    baseURL: llmProxyBaseUrl,
  });
  const agent = new TravelPlannerAgent(store, provider, editorial, weather);
  if (mode !== "demo") void mcp.start().catch(() => undefined);
  return {
    store,
    provider,
    agent,
    intentInterpreter,
    readiness: () => {
      const checkedAt = new Date().toISOString();
      const real = mode !== "demo";
      const mcpState = mcp.readiness();
      const mcpError = readableMcpError(mcpState.error);
      const sources: SystemReadiness["sources"] = [
        {
          id: "mcp",
          status: mcpState.connected ? "ready" : "disconnected",
          required: real,
          message: mcpState.connected
            ? "Локальный MCP запущен"
            : mcpError ?? (existsSync(env.TBANK_MCP_COMMAND) ? "MCP запускается" : "Команда MCP не найдена"),
        },
        {
          id: "bankSession",
          status: existsSync(env.TBANK_SESSION_PATH) ? "ready" : "not_configured",
          required: real,
          message: existsSync(env.TBANK_SESSION_PATH)
            ? "Сохранённая банковская сессия найдена"
            : "Сохранённая банковская сессия не найдена",
        },
        {
          id: "llmProxy",
          status: llmProxyApiKey ? "ready" : "not_configured",
          required: false,
          message: llmProxyApiKey
            ? `Описание поездки, персональное оформление и команды разбирает ${llmProxyModel} через внутренний LLM Proxy`
            : "LLM Proxy не настроен; добавьте LLM_PROXY_API_KEY, чтобы включить описание словами и команды чата",
        },
        {
          id: "2gis",
          status: twoGisApiKey ? "ready" : "not_configured",
          required: false,
          message: twoGisApiKey
            ? "2ГИС настроен как основной источник ресторанов; OpenStreetMap остаётся резервным"
            : "Ключ 2ГИС не задан; рестораны ищутся через OpenStreetMap",
        },
        {
          id: "overpass",
          status: "ready",
          required: false,
          message: "Overpass настроен; доступность проверяется во время поиска",
        },
        {
          id: "nominatim",
          status: "ready",
          required: false,
          message: "Nominatim настроен; используется только при отсутствии координат отеля",
        },
        {
          id: "weather",
          status: "ready",
          required: false,
          message: "Open-Meteo настроен; доступность проверяется при сборке поездки",
        },
      ];
      return {
        status: sources.some((source) => source.required && source.status !== "ready")
          ? "degraded"
          : "ready",
        dataMode: provider.dataMode,
        checkedAt,
        sources,
      };
    },
    close: async () => {
      await provider.close();
      store.close();
    },
  };
}
