import type { Response } from "express";
import { Router } from "express";
import {
  tripBriefInterpretationRequestSchema,
  tripBriefSchema,
  tripMessageSchema,
  type SystemReadiness,
} from "@travel-growth-inspiration/contracts";
import { z } from "zod";

import { AppError } from "../../http/app-error.js";
import { cities } from "../catalog/cities.js";
import { TravelStore } from "../storage/travel-store.js";
import { TravelPlannerAgent } from "./travel-planner-agent.js";
import {
  TripIntentInputError,
  TripIntentUnavailableError,
  type TripIntentInterpreter,
} from "./trip-intent-interpreter.js";

export type PlannerRouteDependencies = {
  store: TravelStore;
  agent: TravelPlannerAgent;
  intentInterpreter: TripIntentInterpreter;
  readiness: () => SystemReadiness;
};

function parseOrThrow<T>(schema: z.ZodType<T>, value: unknown): T {
  const parsed = schema.safeParse(value);
  if (!parsed.success) {
    throw new AppError(400, "VALIDATION_ERROR", "Некорректные параметры запроса", {
      issues: parsed.error.issues,
    });
  }
  return parsed.data;
}

function sendEvent(response: Response, event: { id: number; type: string; data: unknown }): void {
  response.write(`id: ${event.id}\n`);
  response.write(`event: ${event.type}\n`);
  response.write(`data: ${JSON.stringify(event.data)}\n\n`);
}

export function createPlannerRouter({
  store,
  agent,
  intentInterpreter,
  readiness,
}: PlannerRouteDependencies): Router {
  const router = Router();

  router.get("/catalog/cities", (_request, response) => {
    response.json({ cities });
  });

  router.get("/system/readiness", (_request, response) => {
    response.json(readiness());
  });

  router.post("/trip-briefs/interpret", async (request, response) => {
    const input = parseOrThrow(tripBriefInterpretationRequestSchema, request.body);
    try {
      response.json(await intentInterpreter.interpret(input));
    } catch (error) {
      if (error instanceof TripIntentInputError) {
        throw new AppError(400, "TRIP_INTENT_INVALID", error.message);
      }
      if (error instanceof TripIntentUnavailableError) {
        throw new AppError(503, "TEXT_INTERPRETATION_UNAVAILABLE", error.message);
      }
      throw error;
    }
  });

  router.post("/trip-runs", (request, response) => {
    const brief = parseOrThrow(tripBriefSchema, request.body);
    response.status(202).json(agent.createRun(brief));
  });

  router.get("/trip-runs/:runId", (request, response) => {
    const run = store.getRun(String(request.params.runId));
    if (!run) throw new AppError(404, "TRIP_RUN_NOT_FOUND", "Подбор поездки не найден");
    response.json(run);
  });

  router.get("/jobs/:jobId/events", (request, response) => {
    const jobId = String(request.params.jobId);
    const job = store.getJob(jobId);
    if (!job) throw new AppError(404, "JOB_NOT_FOUND", "Задание не найдено");
    const headerId = Number(request.headers["last-event-id"] ?? 0);
    const queryId = Number(request.query.after ?? 0);
    let lastSent = Number.isFinite(headerId) && headerId > 0 ? headerId : queryId;

    response.status(200);
    response.setHeader("content-type", "text/event-stream; charset=utf-8");
    response.setHeader("cache-control", "no-cache, no-transform");
    response.setHeader("connection", "keep-alive");
    response.setHeader("x-accel-buffering", "no");
    response.flushHeaders();

    for (const event of store.getEvents(jobId, lastSent)) {
      sendEvent(response, event);
      lastSent = event.id;
    }
    const latestJob = store.getJob(jobId);
    if (
      latestJob?.status === "completed" ||
      latestJob?.status === "failed" ||
      latestJob?.status === "interrupted"
    ) {
      response.end();
      return;
    }

    const unsubscribe = store.subscribe(jobId, (event) => {
      if (event.id <= lastSent) return;
      sendEvent(response, event);
      lastSent = event.id;
      if (event.type === "job.completed" || event.type === "job.failed") {
        cleanup();
        response.end();
      }
    });
    const heartbeat = setInterval(() => response.write(": heartbeat\n\n"), 15_000);
    const cleanup = () => {
      clearInterval(heartbeat);
      unsubscribe();
    };
    request.once("close", cleanup);
  });

  router.get("/trips/:tripId", (request, response) => {
    const trip = store.getTrip(String(request.params.tripId));
    if (!trip) throw new AppError(404, "TRIP_NOT_FOUND", "Поездка не найдена");
    response.json(trip);
  });

  router.get("/trips/:tripId/messages", (request, response) => {
    const tripId = String(request.params.tripId);
    if (!store.getTrip(tripId)) throw new AppError(404, "TRIP_NOT_FOUND", "Поездка не найдена");
    response.json({ messages: store.getMessages(tripId) });
  });

  router.post("/trips/:tripId/messages", (request, response) => {
    const input = parseOrThrow(tripMessageSchema, request.body);
    response.status(202).json(agent.postMessage(String(request.params.tripId), input));
  });

  router.post("/trips/:tripId/refresh", (request, response) => {
    response.status(202).json(agent.refresh(String(request.params.tripId)));
  });

  return router;
}
