import { config as loadEnv } from "dotenv";
import { z } from "zod";

import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

const travelApiRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

// Explicit process environment has the highest priority. Project settings live
// in .env, while the LLM Proxy secret may be kept separately in config.env.
loadEnv({ path: path.join(travelApiRoot, ".env"), quiet: true });
if (!process.env.LLM_PROXY_API_KEY?.trim()) {
  delete process.env.LLM_PROXY_API_KEY;
  loadEnv({ path: path.join(travelApiRoot, "config.env"), quiet: true });
}

const optionalSecret = z.preprocess(
  (value) => typeof value === "string" && !value.trim() ? undefined : value,
  z.string().min(1).optional(),
);

const envSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  HOST: z.string().min(1).default("127.0.0.1"),
  PORT: z.coerce.number().int().min(1).max(65_535).default(3_000),
  DATABASE_PATH: z.string().min(1).default(path.resolve(process.cwd(), "data/travel-nova.sqlite")),
  TBANK_MCP_COMMAND: z
    .string()
    .min(1)
    .default(path.resolve(process.cwd(), "../tbank-mcp/bin/tbank-mcp")),
  TBANK_SESSION_PATH: z
    .string()
    .min(1)
    .default(path.join(os.homedir(), ".local/share/tbank-mcp/session.json")),
  LLM_PROXY_API_KEY: optionalSecret,
  LLM_PROXY_BASE_URL: z.string().url().default("https://llm-proxy.t-tech.team/v1"),
  LLM_PROXY_MODEL: z.string().min(1).default("tgpt/text.instant.medium"),
  OVERPASS_URL: z.string().url().default("https://overpass-api.de/api/interpreter"),
  NOMINATIM_URL: z.string().url().default("https://nominatim.openstreetmap.org"),
  TWOGIS_API_KEY: optionalSecret,
  TWOGIS_PLACES_URL: z.string().url().default("https://catalog.api.2gis.com/3.0/items"),
  OPEN_METEO_FORECAST_URL: z.string().url().default("https://api.open-meteo.com/v1/forecast"),
  OPEN_METEO_ARCHIVE_URL: z.string().url().default("https://archive-api.open-meteo.com/v1/archive"),
  PROVIDER_TIMEOUT_MS: z.coerce.number().int().min(1_000).max(60_000).default(15_000),
  HOTEL_PROVIDER_TIMEOUT_MS: z.coerce.number().int().min(5_000).max(60_000).default(35_000),
  FLIGHT_PROVIDER_TIMEOUT_MS: z.coerce.number().int().min(5_000).max(60_000).default(45_000),
  MCP_MAX_CONCURRENCY: z.coerce.number().int().min(1).max(8).default(3),
  MCP_FLIGHT_MAX_CONCURRENCY: z.coerce.number().int().min(1).max(12).default(6),
  MCP_HOTEL_MAX_CONCURRENCY: z.coerce.number().int().min(1).max(8).default(3),
  DATA_MODE: z.enum(["auto", "live", "demo"]).default("demo"),
});

const parsed = envSchema.safeParse(process.env);

if (!parsed.success) {
  const details = z.prettifyError(parsed.error);
  throw new Error(`Invalid environment configuration:\n${details}`);
}

export const env = parsed.data;
