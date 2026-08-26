import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("API responses", () => {
  it("keeps a structured API error message", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      error: { message: "Поездка уже изменилась; обновите страницу" },
    }), {
      status: 409,
      headers: { "content-type": "application/json" },
    })));

    await expect(api.message("trip-1", {
      text: "Хочу прилететь раньше",
      baseRevisionId: "revision-1",
    })).rejects.toThrow("Поездка уже изменилась; обновите страницу");
  });

  it("explains an empty proxy error without exposing a JSON parser failure", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("", { status: 502 })));

    await expect(api.message("trip-1", {
      text: "Хочу прилететь раньше",
      baseRevisionId: "revision-1",
    })).rejects.toThrow("Сервис временно не ответил (HTTP 502). Попробуйте ещё раз.");
  });

  it("explains a truncated successful response", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{", { status: 200 })));

    await expect(api.trip("trip-1")).rejects.toThrow(
      "Сервис вернул неполный ответ. Попробуйте ещё раз.",
    );
  });
});
