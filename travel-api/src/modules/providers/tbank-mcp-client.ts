import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { z } from "zod";

const SAFE_TOOLS = new Set([
  "list_accounts",
  "list_operations",
  "spending_categories",
  "orders",
  "order_details",
  "travel_order_details",
  "audience_profile",
  "flight_history",
  "flight_search",
  "hotel_autocomplete",
  "hotel_search",
  "hotel_details",
  "afisha_catalog",
  "afisha_places",
  "concert_schedule",
]);

const envelopeSchema = z.discriminatedUnion("ok", [
  z.object({
    ok: z.literal(true),
    data: z.unknown(),
    source: z.string(),
    checkedAt: z.string(),
    warnings: z.array(z.string()),
    meta: z.record(z.string(), z.unknown()),
  }),
  z.object({
    ok: z.literal(false),
    data: z.null(),
    source: z.string(),
    checkedAt: z.string(),
    warnings: z.array(z.string()),
    meta: z.record(z.string(), z.unknown()),
    error: z.object({ code: z.string(), message: z.string() }),
  }),
]);

export type McpJsonResult<T> = {
  data: T;
  source: string;
  checkedAt: string;
  warnings: string[];
  meta: Record<string, unknown>;
};

export type TbankMcpReadiness = {
  connected: boolean;
  restartUsed: boolean;
  error?: string;
};

type ConcurrencyLane = "default" | "flights" | "hotels";

type LaneState = {
  activeCalls: number;
  maxConcurrency: number;
  waiters: Array<() => void>;
};

export class TbankMcpClient {
  readonly #command: string;
  readonly #timeoutMs: number;
  readonly #lanes: Record<ConcurrencyLane, LaneState>;
  #client: Client | undefined = undefined;
  #transport: StdioClientTransport | undefined = undefined;
  #connecting: Promise<void> | undefined = undefined;
  #restartUsed = false;
  #lastError: string | undefined = undefined;
  constructor(
    command: string,
    timeoutMs: number,
    maxConcurrency = 3,
    flightMaxConcurrency = 6,
    hotelMaxConcurrency = 3,
  ) {
    this.#command = command;
    this.#timeoutMs = timeoutMs;
    this.#lanes = {
      default: { activeCalls: 0, maxConcurrency, waiters: [] },
      flights: { activeCalls: 0, maxConcurrency: flightMaxConcurrency, waiters: [] },
      hotels: { activeCalls: 0, maxConcurrency: hotelMaxConcurrency, waiters: [] },
    };
  }

  async #connect(): Promise<void> {
    if (this.#client) return;
    if (this.#connecting) return this.#connecting;
    this.#connecting = (async () => {
      const transport = new StdioClientTransport({
        command: this.#command,
        args: [],
        stderr: "pipe",
      });
      const client = new Client({ name: "travel-nova-api", version: "0.1.0" });
      try {
        await client.connect(transport);
      } catch (error) {
        await transport.close().catch(() => undefined);
        throw error;
      }
      this.#transport = transport;
      this.#client = client;
      this.#lastError = undefined;
    })();
    try {
      await this.#connecting;
    } finally {
      this.#connecting = undefined;
    }
  }

  async call(
    name: string,
    args: Record<string, unknown> = {},
    timeoutMs = this.#timeoutMs,
  ): Promise<string> {
    if (!SAFE_TOOLS.has(name)) {
      throw new Error(`MCP tool is not in the Travel Nova read-only allowlist: ${name}`);
    }
    const release = await this.#acquire(name);
    try {
      return await this.#callOnce(name, args, timeoutMs);
    } catch (error) {
      this.#lastError = error instanceof Error ? error.message : "Неизвестная ошибка MCP";
      if (this.#restartUsed || !this.#isTransportFailure(error)) throw error;
      this.#restartUsed = true;
      await this.#reset();
      return this.#callOnce(name, args, timeoutMs);
    } finally {
      release();
    }
  }

  async start(): Promise<void> {
    try {
      await this.#connect();
    } catch (error) {
      this.#lastError = error instanceof Error ? error.message : "Не удалось запустить MCP";
      throw error;
    }
  }

  async callJson<T>(
    name: string,
    args: Record<string, unknown>,
    dataSchema: z.ZodType<T>,
    timeoutMs = this.#timeoutMs,
  ): Promise<McpJsonResult<T>> {
    const text = await this.call(name, { ...args, response_format: "json" }, timeoutMs);
    let payload: unknown;
    try {
      payload = JSON.parse(text);
    } catch {
      throw new Error(`MCP tool ${name} returned invalid JSON`);
    }
    const envelope = envelopeSchema.safeParse(payload);
    if (!envelope.success) {
      throw new Error(`MCP tool ${name} returned an invalid response envelope`);
    }
    if (!envelope.data.ok) {
      throw new Error(`${envelope.data.error.code}: ${envelope.data.error.message}`);
    }
    const data = dataSchema.safeParse(envelope.data.data);
    if (!data.success) {
      const issues = data.error.issues
        .slice(0, 4)
        .map((issue) => `${issue.path.join(".") || "data"}: ${issue.message}`)
        .join("; ");
      throw new Error(
        `MCP tool ${name} returned data that does not match its JSON contract${issues ? ` (${issues})` : ""}`,
      );
    }
    return {
      data: data.data,
      source: envelope.data.source,
      checkedAt: envelope.data.checkedAt,
      warnings: envelope.data.warnings,
      meta: envelope.data.meta,
    };
  }

  readiness(): TbankMcpReadiness {
    return {
      connected: Boolean(this.#client),
      restartUsed: this.#restartUsed,
      ...(this.#lastError ? { error: this.#lastError } : {}),
    };
  }

  async #callOnce(
    name: string,
    args: Record<string, unknown>,
    timeoutMs: number,
  ): Promise<string> {
    await this.#connect();
    const client = this.#client;
    if (!client) throw new Error("T-Bank MCP client is not connected");
    let result: Awaited<ReturnType<Client["callTool"]>>;
    try {
      result = await client.callTool(
        { name, arguments: args },
        undefined,
        { timeout: timeoutMs },
      );
    } catch (error) {
      const text = error instanceof Error ? error.message : String(error);
      if (/timed out|timeout/iu.test(text)) {
        throw new Error(`MCP tool ${name} timed out`, { cause: error });
      }
      throw error;
    }
    const content = Array.isArray(result.content) ? result.content : [];
    const text = content
      .filter((item): item is { type: "text"; text: string } => item.type === "text")
      .map((item) => item.text)
      .join("\n")
      .trim();
    if (!text) throw new Error(`MCP tool ${name} returned no text`);
    if (/^(?:Ошибка|ERR\b|❌)/iu.test(text)) throw new Error(text);
    return text;
  }

  async #acquire(toolName: string): Promise<() => void> {
    const lane = this.#lanes[this.#laneFor(toolName)];
    if (lane.activeCalls >= lane.maxConcurrency) {
      await new Promise<void>((resolve) => lane.waiters.push(resolve));
    }
    lane.activeCalls += 1;
    let released = false;
    return () => {
      if (released) return;
      released = true;
      lane.activeCalls -= 1;
      lane.waiters.shift()?.();
    };
  }

  #laneFor(toolName: string): ConcurrencyLane {
    if (toolName === "flight_search") return "flights";
    if (toolName.startsWith("hotel_")) return "hotels";
    return "default";
  }

  #isTransportFailure(error: unknown): boolean {
    const text = error instanceof Error ? error.message : String(error);
    return /connection closed|not connected|econnreset|epipe|transport.*closed|spawn|process.*exit/iu.test(text);
  }

  async #reset(): Promise<void> {
    try {
      await this.#transport?.close();
    } catch {
      // The child may already be gone.
    }
    this.#client = undefined;
    this.#transport = undefined;
  }

  async close(): Promise<void> {
    await this.#reset();
  }
}
