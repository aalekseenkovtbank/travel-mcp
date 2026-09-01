import { EventEmitter } from "node:events";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { DatabaseSync } from "node:sqlite";

import {
  chatMessageActionSchema,
  type ChatMessage,
  type ChatMessageAction,
  type Completeness,
  type DataMode,
  type JobEvent,
  type JobEventType,
  type JobStatus,
  type PreferenceProfile,
  type Restaurant,
  type RestaurantGroup,
  type TripBrief,
  type TripDetail,
  type TripProposal,
  type TripRevision,
  type TripRunSnapshot,
  type SourceStatus,
} from "@travel-growth-inspiration/contracts";
import { emptyBehavioralInsights } from "../providers/behavioral-profile.js";

type JobRecord = {
  id: string;
  status: JobStatus;
  runId?: string;
  tripId?: string;
  error?: string;
};

type DatabaseRow = Record<string, unknown>;

function now(): string {
  return new Date().toISOString();
}

function parseJson<T>(value: unknown): T {
  return JSON.parse(String(value)) as T;
}

function normalizeProfile(profile: PreferenceProfile): PreferenceProfile {
  return {
    ...profile,
    profileVersion: profile.profileVersion ?? 1,
    analysisWindowDays: profile.analysisWindowDays ?? 90,
    transactionCount: profile.transactionCount ?? 0,
    estimatedMonthlyIncomeRub: profile.estimatedMonthlyIncomeRub ?? 0,
    incomeCohort: profile.incomeCohort ?? "unknown",
    incomeConfidence: profile.incomeConfidence ?? "unavailable",
    weekendAverageDailySpendRub: profile.weekendAverageDailySpendRub ?? 0,
    weekdayAverageDailySpendRub: profile.weekdayAverageDailySpendRub ?? 0,
    weekendSpendSharePct: profile.weekendSpendSharePct ?? 0,
    averageCheckRub: profile.averageCheckRub ?? 0,
    medianCheckRub: profile.medianCheckRub ?? 0,
    categoryBreakdown: profile.categoryBreakdown ?? [],
    diningProfile: profile.diningProfile ?? {
      averageCheckRub: 0,
      medianCheckRub: 0,
      preferredCuisines: [],
      preferredVenueTypes: [],
    },
    shoppingProfile: profile.shoppingProfile ?? {
      averageCheckRub: 0,
      medianCheckRub: 0,
      preferredStoreTypes: [],
    },
    // Legacy snapshots may contain merchant names. Strip them when loading into a run.
    favoriteMerchants: [],
    favoriteDiningMerchants: [],
    behavioralInsights: profile.behavioralInsights ?? emptyBehavioralInsights(),
    llmSummary: profile.llmSummary ?? "Сохранённый профиль без расширенной аналитики.",
  };
}

type LegacyProposal = Omit<TripProposal, "events" | "restaurantGroups" | "weather"> & {
  events?: TripProposal["events"];
  event?: TripProposal["events"][number];
  restaurantGroups?: RestaurantGroup[];
  restaurants?: Restaurant[];
  weather?: TripProposal["weather"];
};

function normalizeRestaurant(restaurant: Restaurant): Restaurant {
  return {
    ...restaurant,
    matchReasons: restaurant.matchReasons?.length
      ? restaurant.matchReasons
      : [`${restaurant.distanceMeters} м от отеля.`],
  };
}

function normalizeProposal(value: unknown): TripProposal {
  const legacy = value as LegacyProposal;
  const events = legacy.events ?? (legacy.event ? [legacy.event] : []);
  const restaurantGroups = legacy.restaurantGroups?.map((group) => ({
    ...group,
    restaurants: group.restaurants.map(normalizeRestaurant).slice(0, 3),
  })) ?? (legacy.restaurants?.length
    ? [{
        id: `restaurants-hotel-${legacy.hotel.hotelId}`,
        anchorType: "hotel" as const,
        anchorId: legacy.hotel.hotelId,
        anchorName: legacy.hotel.name,
        anchorMapPointId: legacy.hotel.mapPoint.id,
        availability: legacy.restaurants[0]?.availability ?? {
          component: "nearby" as const,
          availability: "available" as const,
          required: false,
          source: "Сохранённая поездка",
          checkedAt: legacy.generatedAt,
        },
        restaurants: legacy.restaurants.map(normalizeRestaurant).slice(0, 3),
      }]
    : []);
  const restaurantPointIds = new Set(
    restaurantGroups.flatMap((group) => group.restaurants.map((restaurant) => restaurant.mapPoint.id)),
  );
  const { event: _event, restaurants: _restaurants, ...proposal } = legacy;
  return {
    ...proposal,
    events,
    restaurantGroups,
    weather: legacy.weather ?? { days: [] },
    itinerary: legacy.itinerary.filter((item) =>
      !/^Обед:/u.test(item.title) && (!item.mapPointId || !restaurantPointIds.has(item.mapPointId)),
    ),
  } as TripProposal;
}

export class TravelStore {
  readonly #database: DatabaseSync;
  readonly #events = new EventEmitter();

  constructor(databasePath: string) {
    if (databasePath !== ":memory:") {
      mkdirSync(path.dirname(path.resolve(databasePath)), { recursive: true });
    }
    this.#database = new DatabaseSync(databasePath);
    this.#database.exec("PRAGMA foreign_keys = ON; PRAGMA journal_mode = WAL;");
    this.#migrate();
  }

  #migrate(): void {
    this.#database.exec(`
      CREATE TABLE IF NOT EXISTS trip_runs (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        brief_json TEXT NOT NULL,
        profile_json TEXT,
        warnings_json TEXT NOT NULL DEFAULT '[]',
        data_mode TEXT NOT NULL DEFAULT 'real',
        completeness TEXT NOT NULL DEFAULT 'failed',
        sources_json TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS trips (
        id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL REFERENCES trip_runs(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS trip_revisions (
        id TEXT PRIMARY KEY,
        trip_id TEXT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
        revision INTEGER NOT NULL,
        brief_json TEXT NOT NULL,
        proposal_json TEXT NOT NULL,
        change_summary_json TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL,
        UNIQUE(trip_id, revision)
      );

      CREATE TABLE IF NOT EXISTS chat_messages (
        id TEXT PRIMARY KEY,
        trip_id TEXT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        actions_json TEXT NOT NULL DEFAULT '[]',
        revision_id TEXT,
        created_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        status TEXT NOT NULL,
        run_id TEXT,
        trip_id TEXT,
        error TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS job_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
        event_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS profile_snapshots (
        id TEXT PRIMARY KEY,
        profile_json TEXT NOT NULL,
        created_at TEXT NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_trips_run_id ON trips(run_id);
      CREATE INDEX IF NOT EXISTS idx_revisions_trip_id ON trip_revisions(trip_id, revision);
      CREATE INDEX IF NOT EXISTS idx_messages_trip_id ON chat_messages(trip_id, created_at);
      CREATE INDEX IF NOT EXISTS idx_job_events_job_id ON job_events(job_id, id);
      CREATE INDEX IF NOT EXISTS idx_profile_snapshots_created_at ON profile_snapshots(created_at DESC);
    `);
    this.#ensureColumn("trip_runs", "data_mode", "TEXT NOT NULL DEFAULT 'real'");
    this.#ensureColumn("trip_runs", "completeness", "TEXT NOT NULL DEFAULT 'failed'");
    this.#ensureColumn("trip_runs", "sources_json", "TEXT NOT NULL DEFAULT '[]'");
    this.#ensureColumn("trip_revisions", "change_summary_json", "TEXT NOT NULL DEFAULT '[]'");
    this.#ensureColumn("chat_messages", "actions_json", "TEXT NOT NULL DEFAULT '[]'");
    this.#recoverInterruptedWork();
  }

  #ensureColumn(table: string, column: string, definition: string): void {
    const columns = this.#database.prepare(`PRAGMA table_info(${table})`).all() as DatabaseRow[];
    if (columns.some((item) => String(item.name) === column)) return;
    this.#database.exec(`ALTER TABLE ${table} ADD COLUMN ${column} ${definition}`);
  }

  #recoverInterruptedWork(): void {
    const timestamp = now();
    this.#database
      .prepare("UPDATE jobs SET status = 'interrupted', error = ?, updated_at = ? WHERE status IN ('queued', 'running')")
      .run("Задание прервано перезапуском сервиса", timestamp);
    const rows = this.#database
      .prepare("SELECT id, warnings_json FROM trip_runs WHERE status IN ('queued', 'running')")
      .all() as DatabaseRow[];
    for (const row of rows) {
      const warnings = parseJson<string[]>(row.warnings_json);
      const warning = "Подбор был прерван перезапуском сервиса; запустите его повторно.";
      if (!warnings.includes(warning)) warnings.push(warning);
      this.#database
        .prepare("UPDATE trip_runs SET status = 'failed', completeness = 'failed', warnings_json = ?, updated_at = ? WHERE id = ?")
        .run(JSON.stringify(warnings), timestamp, String(row.id));
    }
  }

  close(): void {
    this.#database.close();
  }

  createRun(brief: TripBrief, dataMode: DataMode): string {
    const id = randomUUID();
    const timestamp = now();
    this.#database
      .prepare(
        "INSERT INTO trip_runs (id, status, brief_json, data_mode, completeness, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
      )
      .run(id, "queued", JSON.stringify(brief), dataMode, "failed", timestamp, timestamp);
    return id;
  }

  setRunStatus(runId: string, status: JobStatus): void {
    this.#database
      .prepare("UPDATE trip_runs SET status = ?, updated_at = ? WHERE id = ?")
      .run(status, now(), runId);
  }

  setRunProfile(runId: string, profile: PreferenceProfile): void {
    this.#database
      .prepare("UPDATE trip_runs SET profile_json = ?, updated_at = ? WHERE id = ?")
      .run(JSON.stringify(profile), now(), runId);
  }

  setRunResultMetadata(runId: string, completeness: Completeness, sources: SourceStatus[]): void {
    this.#database
      .prepare("UPDATE trip_runs SET completeness = ?, sources_json = ?, updated_at = ? WHERE id = ?")
      .run(completeness, JSON.stringify(sources), now(), runId);
  }

  saveProfileSnapshot(profile: PreferenceProfile): void {
    this.#database
      .prepare("INSERT INTO profile_snapshots (id, profile_json, created_at) VALUES (?, ?, ?)")
      .run(randomUUID(), JSON.stringify(profile), now());
  }

  getLatestProfileSnapshot(maxAgeMs: number): PreferenceProfile | undefined {
    const row = this.#database
      .prepare("SELECT profile_json, created_at FROM profile_snapshots ORDER BY created_at DESC LIMIT 1")
      .get() as DatabaseRow | undefined;
    if (!row || Date.now() - Date.parse(String(row.created_at)) > maxAgeMs) return undefined;
    const profile = parseJson<PreferenceProfile>(row.profile_json);
    // Version 2 introduced audience-safe and purchase-derived behavioral signals.
    // Recompute old snapshots once instead of serving an apparently complete empty profile.
    if ((profile.profileVersion ?? 1) < 2) return undefined;
    return normalizeProfile(profile);
  }

  addRunWarning(runId: string, warning: string): void {
    const row = this.#database
      .prepare("SELECT warnings_json FROM trip_runs WHERE id = ?")
      .get(runId) as DatabaseRow | undefined;
    if (!row) return;
    const warnings = parseJson<string[]>(row.warnings_json);
    if (!warnings.includes(warning)) warnings.push(warning);
    this.#database
      .prepare("UPDATE trip_runs SET warnings_json = ?, updated_at = ? WHERE id = ?")
      .run(JSON.stringify(warnings), now(), runId);
  }

  createJob(type: "compile" | "chat" | "refresh", refs: { runId?: string; tripId?: string }): string {
    const id = randomUUID();
    const timestamp = now();
    this.#database
      .prepare(
        "INSERT INTO jobs (id, type, status, run_id, trip_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
      )
      .run(id, type, "queued", refs.runId ?? null, refs.tripId ?? null, timestamp, timestamp);
    return id;
  }

  updateJob(jobId: string, status: JobStatus, error?: string): void {
    this.#database
      .prepare("UPDATE jobs SET status = ?, error = ?, updated_at = ? WHERE id = ?")
      .run(status, error ?? null, now(), jobId);
  }

  getJob(jobId: string): JobRecord | undefined {
    const row = this.#database.prepare("SELECT * FROM jobs WHERE id = ?").get(jobId) as
      | DatabaseRow
      | undefined;
    if (!row) return undefined;
    return {
      id: String(row.id),
      status: String(row.status) as JobStatus,
      ...(row.run_id ? { runId: String(row.run_id) } : {}),
      ...(row.trip_id ? { tripId: String(row.trip_id) } : {}),
      ...(row.error ? { error: String(row.error) } : {}),
    };
  }

  appendEvent(jobId: string, type: JobEventType, data: Record<string, unknown>): JobEvent {
    const createdAt = now();
    const result = this.#database
      .prepare(
        "INSERT INTO job_events (job_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
      )
      .run(jobId, type, JSON.stringify(data), createdAt);
    const event: JobEvent = {
      id: Number(result.lastInsertRowid),
      jobId,
      type,
      data,
      createdAt,
    };
    this.#events.emit(`job:${jobId}`, event);
    return event;
  }

  getEvents(jobId: string, afterId = 0): JobEvent[] {
    const rows = this.#database
      .prepare("SELECT * FROM job_events WHERE job_id = ? AND id > ? ORDER BY id ASC")
      .all(jobId, afterId) as DatabaseRow[];
    return rows.map((row) => ({
      id: Number(row.id),
      jobId: String(row.job_id),
      type: String(row.event_type) as JobEventType,
      data: parseJson<Record<string, unknown>>(row.payload_json),
      createdAt: String(row.created_at),
    }));
  }

  subscribe(jobId: string, listener: (event: JobEvent) => void): () => void {
    const eventName = `job:${jobId}`;
    this.#events.on(eventName, listener);
    return () => this.#events.off(eventName, listener);
  }

  createTrip(runId: string, proposal: TripProposal, brief: TripBrief): TripRevision {
    const tripId = proposal.id;
    const timestamp = now();
    this.#database.exec("BEGIN IMMEDIATE");
    try {
      this.#database
        .prepare("INSERT INTO trips (id, run_id, created_at) VALUES (?, ?, ?)")
        .run(tripId, runId, timestamp);
      const revision = this.addRevision(tripId, brief, proposal);
      this.#database.exec("COMMIT");
      return revision;
    } catch (error) {
      this.#database.exec("ROLLBACK");
      throw error;
    }
  }

  finalizePreparingTrip(tripId: string, proposal: TripProposal): TripRevision {
    const trip = this.#database
      .prepare(
        `SELECT t.run_id, r.status AS run_status
         FROM trips t
         JOIN trip_runs r ON r.id = t.run_id
         WHERE t.id = ?`,
      )
      .get(tripId) as DatabaseRow | undefined;
    if (!trip) throw new Error("Поездка не найдена");
    if (!["queued", "running"].includes(String(trip.run_status))) {
      throw new Error("Подготовка поездки уже завершена");
    }
    const rows = this.#database
      .prepare("SELECT * FROM trip_revisions WHERE trip_id = ? ORDER BY revision ASC")
      .all(tripId) as DatabaseRow[];
    if (rows.length !== 1 || Number(rows[0]?.revision) !== 1) {
      throw new Error("Подготовительную версию поездки нельзя финализировать");
    }
    const row = rows[0]!;
    const value: TripRevision = {
      id: String(row.id),
      tripId,
      revision: 1,
      brief: parseJson<TripBrief>(row.brief_json),
      proposal: { ...proposal, id: tripId },
      createdAt: String(row.created_at),
    };
    this.#database
      .prepare("UPDATE trip_revisions SET proposal_json = ? WHERE id = ?")
      .run(JSON.stringify(value.proposal), value.id);
    return value;
  }

  addRevision(
    tripId: string,
    brief: TripBrief,
    proposal: TripProposal,
    changeSummary: string[] = [],
  ): TripRevision {
    const latest = this.#database
      .prepare("SELECT MAX(revision) AS revision FROM trip_revisions WHERE trip_id = ?")
      .get(tripId) as DatabaseRow;
    const revision = Number(latest.revision ?? 0) + 1;
    const value: TripRevision = {
      id: randomUUID(),
      tripId,
      revision,
      brief,
      proposal: { ...proposal, id: tripId },
      ...(changeSummary.length ? { changeSummary } : {}),
      createdAt: now(),
    };
    this.#database
      .prepare(
        "INSERT INTO trip_revisions (id, trip_id, revision, brief_json, proposal_json, change_summary_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
      )
      .run(
        value.id,
        tripId,
        revision,
        JSON.stringify(value.brief),
        JSON.stringify(value.proposal),
        JSON.stringify(changeSummary),
        value.createdAt,
      );
    return value;
  }

  getRun(runId: string): TripRunSnapshot | undefined {
    const row = this.#database.prepare("SELECT * FROM trip_runs WHERE id = ?").get(runId) as
      | DatabaseRow
      | undefined;
    if (!row) return undefined;
    const tripRows = this.#database
      .prepare(
        `SELECT r.proposal_json FROM trip_revisions r
         JOIN (SELECT trip_id, MAX(revision) revision FROM trip_revisions GROUP BY trip_id) latest
         ON latest.trip_id = r.trip_id AND latest.revision = r.revision
         JOIN trips t ON t.id = r.trip_id
         WHERE t.run_id = ? ORDER BY t.created_at ASC`,
      )
      .all(runId) as DatabaseRow[];
    return {
      id: String(row.id),
      status: String(row.status) as JobStatus,
      brief: parseJson<TripBrief>(row.brief_json),
      ...(row.profile_json ? { profile: normalizeProfile(parseJson<PreferenceProfile>(row.profile_json)) } : {}),
      trips: tripRows.map((item) => normalizeProposal(parseJson<unknown>(item.proposal_json))),
      warnings: parseJson<string[]>(row.warnings_json),
      dataMode: String(row.data_mode) as DataMode,
      completeness: String(row.completeness) as Completeness,
      sources: parseJson<SourceStatus[]>(row.sources_json),
      createdAt: String(row.created_at),
      updatedAt: String(row.updated_at),
    };
  }

  getTrip(tripId: string): TripDetail | undefined {
    const trip = this.#database.prepare(
      `SELECT t.*, r.status AS run_status
       FROM trips t
       JOIN trip_runs r ON r.id = t.run_id
       WHERE t.id = ?`,
    ).get(tripId) as
      | DatabaseRow
      | undefined;
    if (!trip) return undefined;
    const revision = this.#database
      .prepare("SELECT * FROM trip_revisions WHERE trip_id = ? ORDER BY revision DESC LIMIT 1")
      .get(tripId) as DatabaseRow;
    const count = this.#database
      .prepare("SELECT COUNT(*) AS count FROM trip_revisions WHERE trip_id = ?")
      .get(tripId) as DatabaseRow;
    return {
      id: tripId,
      runId: String(trip.run_id),
      preparationStatus: ["queued", "running"].includes(String(trip.run_status))
        ? "preparing"
        : String(trip.run_status) === "completed"
          ? "ready"
          : "failed",
      latestRevision: this.#rowToRevision(revision),
      revisionCount: Number(count.count),
      createdAt: String(trip.created_at),
    };
  }

  #rowToRevision(row: DatabaseRow): TripRevision {
    return {
      id: String(row.id),
      tripId: String(row.trip_id),
      revision: Number(row.revision),
      brief: parseJson<TripBrief>(row.brief_json),
      proposal: normalizeProposal(parseJson<unknown>(row.proposal_json)),
      ...(parseJson<string[]>(row.change_summary_json ?? "[]").length
        ? { changeSummary: parseJson<string[]>(row.change_summary_json ?? "[]") }
        : {}),
      createdAt: String(row.created_at),
    };
  }

  addMessage(
    tripId: string,
    role: ChatMessage["role"],
    content: string,
    revisionId?: string,
    actions: ChatMessageAction[] = [],
  ): ChatMessage {
    const safeActions = actions.flatMap((action) => {
      const parsed = chatMessageActionSchema.safeParse(action);
      return parsed.success ? [parsed.data] : [];
    });
    const message: ChatMessage = {
      id: randomUUID(),
      tripId,
      role,
      content,
      ...(safeActions.length ? { actions: safeActions } : {}),
      ...(revisionId ? { revisionId } : {}),
      createdAt: now(),
    };
    this.#database
      .prepare(
        "INSERT INTO chat_messages (id, trip_id, role, content, actions_json, revision_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
      )
      .run(
        message.id,
        tripId,
        role,
        content,
        JSON.stringify(safeActions),
        revisionId ?? null,
        message.createdAt,
      );
    return message;
  }

  getMessages(tripId: string): ChatMessage[] {
    const rows = this.#database
      .prepare("SELECT * FROM chat_messages WHERE trip_id = ? ORDER BY created_at ASC")
      .all(tripId) as DatabaseRow[];
    return rows.map((row) => {
      const storedActions = parseJson<unknown>(row.actions_json ?? "[]");
      const actions = (Array.isArray(storedActions) ? storedActions : []).flatMap((action) => {
        const parsed = chatMessageActionSchema.safeParse(action);
        return parsed.success ? [parsed.data] : [];
      });
      return {
        id: String(row.id),
        tripId: String(row.trip_id),
        role: String(row.role) as ChatMessage["role"],
        content: String(row.content),
        ...(actions.length ? { actions } : {}),
        ...(row.revision_id ? { revisionId: String(row.revision_id) } : {}),
        createdAt: String(row.created_at),
      };
    });
  }
}
