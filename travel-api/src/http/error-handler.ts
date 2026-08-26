import type { ErrorRequestHandler } from "express";

import { env } from "../config/env.js";
import { AppError } from "./app-error.js";

export const errorHandler: ErrorRequestHandler = (error, _request, response, _next) => {
  const requestId = String(response.locals.requestId ?? "unknown");

  if (error instanceof AppError) {
    response.status(error.statusCode).json({
      error: {
        code: error.code,
        message: error.message,
        ...(error.details === undefined ? {} : { details: error.details }),
      },
      requestId,
    });
    return;
  }

  const message = error instanceof Error ? error.message : "Unknown error";
  console.error(JSON.stringify({ level: "error", requestId, message }));

  response.status(500).json({
    error: {
      code: "INTERNAL_ERROR",
      message: env.NODE_ENV === "production" ? "Internal server error" : message,
    },
    requestId,
  });
};
