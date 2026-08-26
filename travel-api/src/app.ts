import express from "express";
import helmet from "helmet";

import { errorHandler } from "./http/error-handler.js";
import { notFound } from "./http/not-found.js";
import { requestContext } from "./http/request-context.js";
import { healthRouter } from "./modules/health/health.routes.js";
import {
  createPlannerRouter,
  type PlannerRouteDependencies,
} from "./modules/planner/planner.routes.js";

export function createApp(dependencies?: PlannerRouteDependencies): express.Express {
  const app = express();

  app.disable("x-powered-by");
  app.use(helmet());
  app.use(requestContext);
  app.use(express.json({ limit: "1mb" }));

  app.get("/", (_request, response) => {
    response.json({
      name: "Travel Nova API",
      version: "0.1.0",
      endpoints: {
        health: "/api/v1/health",
        readiness: "/api/v1/system/readiness",
        cities: "/api/v1/catalog/cities",
        interpretBrief: "/api/v1/trip-briefs/interpret",
        tripRuns: "/api/v1/trip-runs",
      },
    });
  });

  app.use("/health", healthRouter);
  app.use("/api/v1/health", healthRouter);
  if (dependencies) app.use("/api/v1", createPlannerRouter(dependencies));

  app.use(notFound);
  app.use(errorHandler);

  return app;
}
