import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { TripBrief, TripProposal, TripRunSnapshot } from "@travel-growth-inspiration/contracts";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("./TripMap", () => ({
  TripMap: ({ points }: { points: unknown[] }) => <div data-testid="trip-map">{points.length} точек</div>,
}));

import { App, TripCard, proposalCover } from "./App";
import { PLANNER_SESSION_KEY, readPlannerSession } from "./planner-session";

const cities = [
  {
    id: "saint-petersburg",
    name: "Санкт-Петербург",
    iata: "LED",
    latitude: 59.9,
    longitude: 30.3,
    tags: ["музеи"],
    accent: "Город на Неве",
  },
  {
    id: "moscow",
    name: "Москва",
    iata: "MOW",
    latitude: 55.7,
    longitude: 37.6,
    tags: ["концерты"],
    accent: "Большой город",
  },
];

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  window.sessionStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.history.pushState({}, "", "/");
});

describe("Travel Nova UI", () => {
  it("migrates a saved v1 planner session without losing form data", () => {
    window.sessionStorage.setItem(PLANNER_SESSION_KEY, JSON.stringify({
      version: 1,
      form: {
        origin: "moscow",
        destination: "",
        adults: 2,
        childrenAges: [],
        timeMode: "exact",
        startDate: "2026-09-18",
        endDate: "2026-09-21",
        windowStart: "2026-09-01",
        windowEnd: "2026-09-30",
        nights: 3,
        budget: "75000",
        interests: ["музеи"],
      },
      proposals: [],
      progress: ["Готово"],
      error: "",
      scrollY: 120,
    }));

    const session = readPlannerSession();
    expect(session?.version).toBe(2);
    expect(session?.mode).toBe("form");
    expect(session?.promptText).toBe("");
    expect(session?.form.origin).toBe("moscow");
    expect(session?.form.budget).toBe("75000");
    expect(session?.progress).toEqual(["Готово"]);
  });

  it("renders the planner without trip presets and supports an optional budget", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
      new Response(
        JSON.stringify(String(input).includes("readiness")
          ? { status: "ready", dataMode: "demo", checkedAt: "2026-08-16T10:00:00Z", sources: [] }
          : { cities }),
        { status: 200, headers: { "content-type": "application/json" } },
    ));
    render(<App />);
    expect(screen.getByRole("heading", { name: /Не ищите билеты/u })).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: /Формат поездки/u })).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Бюджет/u)).toHaveAttribute("placeholder", "Без лимита");
    expect((await screen.findAllByRole("option", { name: /Москва/u })).length).toBe(2);
    expect(await screen.findByText("Демо-данные")).toBeInTheDocument();
  });

  it("interprets a free-text request and starts planning without a confirmation step", async () => {
    const brief = {
      preset: "vacation",
      originCityId: "moscow",
      destinationCityId: "saint-petersburg",
      travelers: { adults: 1, childrenAges: [] },
      time: {
        mode: "flexible",
        windowStart: "2026-08-20",
        windowEnd: "2026-08-31",
        nights: 3,
      },
      interests: ["долгие прогулки"],
      preferences: {
        destinationTags: [{ value: "природа", polarity: "prefer", strength: "soft" }],
        activities: [{ value: "долгие прогулки", polarity: "prefer", strength: "soft" }],
        pace: { value: "active", strength: "soft" },
        climate: { maxDayTemperatureC: 25, strength: "soft" },
        other: [{ value: "без толп", polarity: "avoid", strength: "soft" }],
      },
      intent: {
        summary: "Активный отпуск на природе",
        understood: ["активный темп", "природа", "август", "до +25 °C"],
        assumptions: ["Санкт-Петербург", "1 взрослый", "3 ночи"],
        unverified: ["без толп"],
      },
    } satisfies TripBrief;
    const calls: string[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (init?.method === "POST") calls.push(url);
      if (url.endsWith("/trip-briefs/interpret")) {
        expect(JSON.parse(String(init?.body))).toEqual({
          text: "Хочу активно гулять на природе в прохладном августе без толп",
          defaultOriginCityId: "saint-petersburg",
        });
        return new Response(JSON.stringify({ brief, interpretation: brief.intent }), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.endsWith("/trip-runs") && init?.method === "POST") {
        expect(JSON.parse(String(init.body))).toEqual(brief);
        return new Response(JSON.stringify({ jobId: "job-text", runId: "run-text" }), {
          status: 202,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.endsWith("/trip-runs/run-text")) {
        return new Response(JSON.stringify({
          id: "run-text",
          status: "completed",
          brief,
          trips: [],
          warnings: [],
          dataMode: "demo",
          completeness: "complete",
          sources: [],
          createdAt: "2026-08-19T10:00:00.000Z",
          updatedAt: "2026-08-19T10:00:00.000Z",
        } satisfies TripRunSnapshot), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response(JSON.stringify(url.includes("readiness")
        ? {
            status: "ready",
            dataMode: "demo",
            checkedAt: "2026-08-19T10:00:00.000Z",
            sources: [{
              id: "llmProxy",
              status: "ready",
              required: false,
              message: "LLM Proxy настроен",
            }],
          }
        : { cities }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });

    render(<App />);
    fireEvent.click(screen.getByRole("tab", { name: "Описать словами" }));
    const textarea = screen.getByLabelText(/Расскажите, какой отдых/u);
    const submit = screen.getByRole("button", { name: /Поехали/u });
    expect(submit).toBeDisabled();
    fireEvent.change(textarea, {
      target: { value: "Хочу активно гулять на природе в прохладном августе без толп" },
    });
    fireEvent.click(submit);

    expect(await screen.findByRole("heading", { name: "Активный отпуск на природе" })).toBeInTheDocument();
    expect(screen.getByText("активный темп")).toBeInTheDocument();
    expect(screen.getByText("3 ночи")).toBeInTheDocument();
    expect(screen.getByText("без толп")).toBeInTheDocument();
    await waitFor(() => expect(calls).toEqual([
      "/api/v1/trip-briefs/interpret",
      "/api/v1/trip-runs",
    ]));
    fireEvent.click(screen.getByRole("tab", { name: "Форма" }));
    expect(screen.getByLabelText("Откуда")).toHaveValue("moscow");
  });

  it("shows an honest degraded state for unavailable real sources", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
      new Response(
        JSON.stringify(String(input).includes("readiness")
          ? {
              status: "degraded",
              dataMode: "real",
              checkedAt: "2026-08-16T10:00:00Z",
              sources: [{
                id: "mcp",
                status: "disconnected",
                required: true,
                message: "MCP не запущен",
              }],
            }
          : { cities }),
        { status: 200, headers: { "content-type": "application/json" } },
      ));
    render(<App />);
    expect(await screen.findByText(/Реальные данные · источники не готовы/u)).toBeInTheDocument();
    expect(await screen.findByText(/MCP не запущен/u)).toBeInTheDocument();
  });

  it("restores the form and completed results after returning from a trip", async () => {
    const scrollTo = vi.fn();
    vi.stubGlobal("scrollTo", scrollTo);
    vi.spyOn(window, "scrollY", "get").mockReturnValue(640);
    const checkedAt = "2026-08-16T10:00:00.000Z";
    const proposal = {
      id: "trip-cached",
      runId: "run-cached",
      title: "Казань: сохранённый вариант",
      tagline: "Город для длинных прогулок",
      tier: "balanced",
      destination: {
        id: "kazan",
        name: "Казань",
        iata: "KZN",
        latitude: 55.79,
        longitude: 49.12,
        tags: ["гастрономия"],
        accent: "Татарская столица",
      },
      startDate: "2026-09-18",
      endDate: "2026-09-21",
      travelers: { adults: 1, childrenAges: [] },
      flights: { outbound: { departureTime: "09:20" }, return: {} },
      hotel: { name: "Отель у Кремля", stars: 4 },
      events: [],
      mapPoints: [],
      priceBreakdown: [],
      totalPrice: { amount: 72_000 },
      completeness: "complete",
    } as unknown as TripProposal;
    const snapshot = {
      id: "run-cached",
      status: "completed",
      brief: {},
      trips: [proposal],
      warnings: [],
      dataMode: "demo",
      completeness: "complete",
      sources: [],
      createdAt: checkedAt,
      updatedAt: checkedAt,
    } as unknown as TripRunSnapshot;

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/trip-runs") && init?.method === "POST") {
        return new Response(JSON.stringify({ jobId: "job-cached", runId: "run-cached" }), {
          status: 202,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.endsWith("/trip-runs/run-cached")) {
        return new Response(JSON.stringify(snapshot), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.includes("/trips/")) return await new Promise<Response>(() => undefined);
      return new Response(JSON.stringify(url.includes("readiness")
        ? { status: "ready", dataMode: "demo", checkedAt, sources: [] }
        : { cities }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });

    render(<App />);
    await screen.findAllByRole("option", { name: /Москва/u });
    fireEvent.change(screen.getByLabelText(/Бюджет/u), { target: { value: "75000" } });
    fireEvent.click(screen.getByRole("button", { name: /Показать три путешествия/u }));

    expect(await screen.findByRole("heading", { name: proposal.title })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: `Открыть ${proposal.title}` }));
    expect(await screen.findByText("Открываем поездку…")).toBeInTheDocument();

    act(() => {
      window.history.pushState({}, "", "/");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    expect(await screen.findByRole("heading", { name: proposal.title })).toBeInTheDocument();
    expect(screen.getByLabelText(/Бюджет/u)).toHaveValue(75000);
    await waitFor(() => expect(scrollTo).toHaveBeenCalledWith(0, 640));
  });

  it("opens a preparing trip and replaces it automatically with enriched content", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    window.history.pushState({}, "", "/trips/trip-progressive");
    vi.stubGlobal("scrollTo", vi.fn());
    const checkedAt = "2026-08-16T10:00:00.000Z";
    const flightSource = { component: "flights", availability: "available", required: true, source: "T-Bank Avia", checkedAt } as const;
    const hotelSource = { component: "hotel", availability: "available", required: true, source: "T-Bank Hotels", checkedAt } as const;
    const profileSource = { component: "profile", availability: "available", required: false, source: "T-Bank", checkedAt } as const;
    const hotelPoint = { id: "hotel-progressive", type: "hotel" as const, name: "Отель", latitude: 55.75, longitude: 37.61 };
    const price = (amount: number, source: string) => ({ amount, currency: "RUB" as const, kind: "live" as const, source, checkedAt });
    const base = {
      id: "trip-progressive",
      runId: "run-progressive",
      title: "Москва: готовый маршрут",
      tagline: "Большой город",
      tier: "balanced" as const,
      destination: cities[1]!,
      startDate: "2026-09-18",
      endDate: "2026-09-21",
      travelers: { adults: 1, childrenAges: [] },
      flights: {
        outbound: { direction: "outbound" as const, fromCode: "LED", toCode: "MOW", date: "2026-09-18", summary: "LED → MOW", price: price(5_000, "T-Bank Avia"), availability: flightSource },
        return: { direction: "return" as const, fromCode: "MOW", toCode: "LED", date: "2026-09-21", summary: "MOW → LED", price: price(5_000, "T-Bank Avia"), availability: flightSource },
      },
      hotel: { hotelId: "progressive", name: "Отель", stars: 4, price: price(20_000, "T-Bank Hotels"), mapPoint: hotelPoint, availability: hotelSource },
      events: [],
      restaurantGroups: [],
      itinerary: [{ id: "arrival", day: 1, time: "После прилёта", title: "Заселиться", description: "Спокойный старт", mapPointId: hotelPoint.id }],
      weather: { days: [] },
      mapPoints: [hotelPoint],
      priceBreakdown: [{ label: "Перелёт туда", price: price(5_000, "T-Bank Avia") }],
      totalPrice: { ...price(30_000, "Travel Nova"), kind: "estimated" as const },
      liveSubtotalRub: 30_000,
      estimatedSubtotalRub: 0,
      fitReasons: [],
      warnings: [],
      generatedAt: checkedAt,
      dataMode: "real" as const,
      completeness: "partial" as const,
      sources: [profileSource, flightSource, hotelSource],
    } satisfies TripProposal;
    const eventSource = { component: "event", availability: "available", required: false, source: "T-Bank Afisha", checkedAt } as const;
    const final = {
      ...base,
      events: [{ eventId: "event-ready", name: "Концерт готов", kind: "концерт", dateTime: "2026-09-19T19:00:00", availability: eventSource }],
      sources: [
        ...base.sources,
        eventSource,
        { component: "editorial", availability: "available", required: false, source: "LLM Proxy", checkedAt } as const,
      ],
    } satisfies TripProposal;
    let tripCalls = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/messages")) {
        return new Response(JSON.stringify({ messages: [] }), { status: 200, headers: { "content-type": "application/json" } });
      }
      tripCalls += 1;
      const ready = tripCalls > 1;
      return new Response(JSON.stringify({
        id: base.id,
        runId: base.runId,
        preparationStatus: ready ? "ready" : "preparing",
        latestRevision: { id: "revision-1", tripId: base.id, revision: 1, brief: {}, proposal: ready ? final : base, createdAt: checkedAt },
        revisionCount: 1,
        createdAt: checkedAt,
      }), { status: 200, headers: { "content-type": "application/json" } });
    });

    render(<App />);
    expect(await screen.findByText(/Маршрут уже можно смотреть/u)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Перепроверить все цены/u })).toBeDisabled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });
    expect(await screen.findByText("Концерт готов")).toBeInTheDocument();
    expect(screen.queryByText(/Маршрут уже можно смотреть/u)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Перепроверить все цены/u })).toBeEnabled();
    expect(tripCalls).toBe(2);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4_000);
    });
    expect(tripCalls).toBe(2);
  });

  it("shows a chat revision as soon as trip.ready arrives", async () => {
    window.history.pushState({}, "", "/trips/trip-live");
    vi.stubGlobal("scrollTo", vi.fn());
    const checkedAt = "2026-08-16T10:00:00.000Z";
    const source = {
      component: "nearby" as const,
      availability: "available" as const,
      required: false,
      source: "OpenStreetMap",
      checkedAt,
    };
    const price = (amount: number) => ({
      amount,
      currency: "RUB" as const,
      kind: "live" as const,
      source: "Travel Nova",
      checkedAt,
    });
    const makeProposal = (hotelId: string, hotelName: string, restaurantName: string): TripProposal => {
      const hotelPoint = {
        id: `hotel-${hotelId}`,
        type: "hotel" as const,
        name: hotelName,
        latitude: 55.75,
        longitude: 37.61,
      };
      const restaurantPoint = {
        id: `restaurant-${hotelId}`,
        type: "restaurant" as const,
        name: restaurantName,
        latitude: 55.751,
        longitude: 37.611,
      };
      const restaurant = {
        osmId: `restaurant-${hotelId}`,
        name: restaurantName,
        distanceMeters: 200,
        matchReasons: ["200 м от отеля."],
        mapPoint: restaurantPoint,
        availability: source,
      };
      return {
        id: "trip-live",
        runId: "run-live",
        title: "Москва: маршрут",
        tagline: "Большой город",
        tier: "balanced",
        destination: cities[1]!,
        startDate: "2026-09-18",
        endDate: "2026-09-21",
        travelers: { adults: 1, childrenAges: [] },
        flights: {
          outbound: { direction: "outbound", fromCode: "LED", toCode: "MOW", date: "2026-09-18", summary: "LED → MOW", price: price(5_000), availability: { ...source, component: "flights", required: true } },
          return: { direction: "return", fromCode: "MOW", toCode: "LED", date: "2026-09-21", summary: "MOW → LED", price: price(5_000), availability: { ...source, component: "flights", required: true } },
        },
        hotel: { hotelId, name: hotelName, stars: 4, price: price(20_000), mapPoint: hotelPoint, availability: { ...source, component: "hotel", required: true } },
        events: [],
        restaurantGroups: [{
          id: `restaurants-${hotelId}`,
          anchorType: "hotel",
          anchorId: hotelId,
          anchorName: hotelName,
          anchorMapPointId: hotelPoint.id,
          availability: source,
          restaurants: [restaurant],
        }],
        itinerary: [
          { id: "arrival", day: 1, time: "После прилёта", title: "Заселиться", description: `Спокойный старт рядом с ${hotelName}.`, mapPointId: hotelPoint.id },
          { id: "departure", day: 4, time: "Перед вылетом", title: "Дорога в аэропорт", description: "С запасом времени." },
        ],
        weather: { days: [] },
        mapPoints: [hotelPoint, restaurantPoint],
        priceBreakdown: [
          { label: "Перелёт туда", price: price(5_000) },
          { label: "Перелёт обратно", price: price(5_000) },
          { label: "Отель, 3 ночи", price: price(20_000) },
        ],
        totalPrice: price(30_000),
        liveSubtotalRub: 30_000,
        estimatedSubtotalRub: 0,
        fitReasons: [],
        warnings: [],
        generatedAt: checkedAt,
        dataMode: "real",
        completeness: "complete",
        sources: [
          { ...source, component: "flights", required: true },
          { ...source, component: "hotel", required: true },
          source,
        ],
      };
    };

    class FakeEventSource {
      static readonly instances: FakeEventSource[] = [];
      static readonly CLOSED = 2;
      readyState = 1;
      onerror: (() => void) | null = null;
      readonly listeners = new Map<string, Array<(event: MessageEvent<string>) => void>>();

      constructor(readonly url: string) {
        FakeEventSource.instances.push(this);
      }

      addEventListener(type: string, listener: EventListenerOrEventListenerObject) {
        const listeners = this.listeners.get(type) ?? [];
        listeners.push(listener as (event: MessageEvent<string>) => void);
        this.listeners.set(type, listeners);
      }

      emit(type: string, data: Record<string, unknown>) {
        for (const listener of this.listeners.get(type) ?? []) {
          listener({ data: JSON.stringify(data), lastEventId: "1" } as MessageEvent<string>);
        }
      }

      close() {
        this.readyState = FakeEventSource.CLOSED;
      }
    }
    vi.stubGlobal("EventSource", FakeEventSource);

    let servedProposal = makeProposal("old", "Старый отель", "Кафе у старого отеля");
    let revision = 1;
    let tripReads = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/messages") && init?.method === "POST") {
        return new Response(JSON.stringify({ jobId: "job-live", tripId: "trip-live", messageId: "message-1" }), { status: 202, headers: { "content-type": "application/json" } });
      }
      if (url.endsWith("/messages")) {
        return new Response(JSON.stringify({ messages: [] }), { status: 200, headers: { "content-type": "application/json" } });
      }
      tripReads += 1;
      return new Response(JSON.stringify({
        id: "trip-live",
        runId: "run-live",
        preparationStatus: "ready",
        latestRevision: { id: `revision-${revision}`, tripId: "trip-live", revision, brief: {}, proposal: servedProposal, createdAt: checkedAt },
        revisionCount: revision,
        createdAt: checkedAt,
      }), { status: 200, headers: { "content-type": "application/json" } });
    });

    render(<App />);
    expect(await screen.findByText("Старый отель")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Другой отель" }));
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));

    servedProposal = makeProposal("new", "Новый отель", "Кафе у нового отеля");
    revision = 2;
    act(() => FakeEventSource.instances[0]!.emit("trip.ready", {
      proposal: servedProposal,
      revision: { id: "revision-2", tripId: "trip-live", revision: 2, brief: {}, proposal: servedProposal, createdAt: checkedAt },
    }));

    expect(await screen.findByText("Новый отель")).toBeInTheDocument();
    expect(screen.getByText("Кафе у нового отеля")).toBeInTheDocument();
    expect(tripReads).toBe(1);

    act(() => FakeEventSource.instances[0]!.emit("job.completed", { tripId: "trip-live" }));
    await waitFor(() => expect(tripReads).toBe(2));
  });

  it("shows restaurant groups separately from the timeline", async () => {
    window.history.pushState({}, "", "/trips/trip-1");
    vi.stubGlobal("scrollTo", vi.fn());
    const checkedAt = "2026-08-16T10:00:00.000Z";
    const availability = { component: "nearby", availability: "available", required: false, source: "OpenStreetMap", checkedAt };
    const point = (id: string, type: "hotel" | "restaurant" | "event" | "poi", name: string) => ({
      id, type, name, latitude: 55.75, longitude: 37.61,
    });
    const restaurant = (id: string, name: string, distanceMeters: number) => ({
      osmId: id,
      name,
      cuisine: "regional",
      openingHours: "10:00-23:00",
      distanceMeters,
      matchReasons: [`${distanceMeters} м от точки.`],
      mapPoint: point(`osm-${id}`, "restaurant", name),
      availability,
    });
    const hotelImage = { url: "https://cdn.tbank.ru/hotel.jpg", source: "T-Bank Hotels" };
    const eventImage = { url: "https://kassa.rambler.ru/event.jpg", source: "T-Bank Afisha" };
    const poiImage = {
      url: "https://upload.wikimedia.org/museum.jpg",
      source: "Wikimedia Commons",
      sourceUrl: "https://commons.wikimedia.org/wiki/File:Museum.jpg",
    };
    const technicalEditorialLog = "Персональное оформление временно недоступно: 503 <!doctype html><html><style>huge GPT response</style>";
    const hotelPoint = { ...point("hotel-1", "hotel", "Отель"), image: hotelImage };
    const eventPoint = { ...point("event-1", "event", "Концерт"), image: eventImage };
    const poiPoint = { ...point("poi-1", "poi", "Главный музей"), subtitle: "250 м от отеля", image: poiImage };
    const proposal = {
      id: "trip-1", runId: "run-1", title: "Москва: готовый маршрут", tagline: "Большой город",
      tier: "balanced", destination: cities[1], startDate: "2026-09-18", endDate: "2026-09-21",
      travelers: { adults: 1, childrenAges: [] },
      flights: {
        outbound: { direction: "outbound", fromCode: "LED", toCode: "MOW", date: "2026-09-18", summary: "LED → MOW", price: { amount: 5_000, currency: "RUB", kind: "live", source: "T-Bank", checkedAt }, availability },
        return: { direction: "return", fromCode: "MOW", toCode: "LED", date: "2026-09-21", summary: "MOW → LED", price: { amount: 5_000, currency: "RUB", kind: "live", source: "T-Bank", checkedAt }, availability },
      },
      hotel: { hotelId: "1", name: "Отель", stars: 4, image: hotelImage, price: { amount: 20_000, currency: "RUB", kind: "live", source: "T-Bank", checkedAt }, mapPoint: hotelPoint, availability },
      events: [{ eventId: "1", name: "Концерт", kind: "концерт", dateTime: "2026-09-19T19:00:00", image: eventImage, mapPoint: eventPoint, availability }],
      restaurantGroups: [
        { id: "hotel-group", anchorType: "hotel", anchorId: "1", anchorName: "Отель", anchorMapPointId: hotelPoint.id, availability, restaurants: [restaurant("h1", "У отеля", 200)] },
        { id: "event-group", anchorType: "event", anchorId: "1", anchorName: "Концерт", anchorMapPointId: eventPoint.id, availability, restaurants: [restaurant("e1", "У концерта", 300)] },
      ],
      itinerary: [
        { id: "i1", day: 1, time: "18:00", title: "Прогулка", description: "Перед концертом" },
        { id: "i2", day: 1, time: "19:00", title: "Концерт", description: "Событие из афиши", mapPointId: eventPoint.id },
        { id: "i3", day: 2, time: "11:00", title: "Музей", description: "Дневная программа" },
      ],
      weather: {
        days: [
          {
            date: "2026-09-18",
            kind: "forecast",
            temperatureMinC: 14,
            temperatureMaxC: 19,
            precipitationProbabilityPct: 60,
            weatherCode: 63,
          },
          {
            date: "2026-09-19",
            kind: "climate",
            temperatureMinC: 12,
            temperatureMaxC: 18,
            precipitationFrequencyPct: 32,
            sampleSize: 210,
          },
        ],
      },
      mapPoints: [hotelPoint, eventPoint, poiPoint, point("osm-h1", "restaurant", "У отеля"), point("osm-e1", "restaurant", "У концерта")],
      priceBreakdown: [{ label: "Перелёт туда", price: { amount: 5_000, currency: "RUB", kind: "live", source: "T-Bank", checkedAt } }],
      totalPrice: { amount: 30_000, currency: "RUB", kind: "estimated", source: "Travel Nova", checkedAt },
      liveSubtotalRub: 30_000, estimatedSubtotalRub: 0, fitReasons: [], warnings: [technicalEditorialLog], generatedAt: checkedAt,
      dataMode: "real", completeness: "partial",
      sources: [
        { component: "profile", availability: "available", required: false, source: "T-Bank", checkedAt },
        availability,
        { component: "weather", availability: "available", required: false, source: "Open-Meteo Forecast", checkedAt },
        { component: "editorial", availability: "unavailable", required: false, source: "LLM Proxy или локальный редактор", checkedAt, message: technicalEditorialLog },
      ],
    };
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      return new Response(JSON.stringify(url.endsWith("/messages")
        ? { messages: [] }
        : { id: "trip-1", runId: "run-1", latestRevision: { id: "revision-1", tripId: "trip-1", revision: 1, brief: {}, proposal, createdAt: checkedAt }, revisionCount: 1, createdAt: checkedAt }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Где поесть" })).toBeInTheDocument();
    expect(screen.getByText("осадки 60%")).toBeInTheDocument();
    expect(screen.getByText("осадки 32%")).toBeInTheDocument();
    expect(screen.getByTitle(/Приблизительная оценка по статистике ERA5/u)).toBeInTheDocument();
    expect(screen.getAllByText("прогноз")).toHaveLength(1);
    expect(screen.getByText("У отеля")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Отель" })).toHaveAttribute("loading", "lazy");
    expect(screen.getByRole("img", { name: "Концерт" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Что посмотреть рядом" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Фото: Wikimedia Commons" })).toHaveAttribute(
      "href",
      poiImage.sourceUrl,
    );
    const poiPhoto = screen.getByRole("img", { name: "Главный музей" });
    fireEvent.error(poiPhoto);
    await waitFor(() => expect(screen.queryByRole("img", { name: "Главный музей" })).not.toBeInTheDocument());
    expect(screen.getByText("Главный музей")).toBeInTheDocument();
    expect(screen.queryByText(/Обед:/u)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: /Рядом с: Концерт/u }));
    expect(await screen.findByText("У концерта")).toBeInTheDocument();
    expect(screen.getByText(/Учитываем ваши ресторанные предпочтения/u)).toBeInTheDocument();
    expect(screen.getByText("Локальный редактор · доступен")).toBeInTheDocument();
    expect(screen.queryByText(technicalEditorialLog)).not.toBeInTheDocument();
    expect(screen.queryByText(/часть необязательных источников недоступна/u)).not.toBeInTheDocument();
    expect(screen.queryByText("Важно знать")).not.toBeInTheDocument();

    const typedProposal = proposal as unknown as TripProposal;
    expect(proposalCover(typedProposal)?.image.url).toBe(hotelImage.url);
    const withoutHotelImage = {
      ...typedProposal,
      hotel: { ...typedProposal.hotel, image: undefined },
    };
    expect(proposalCover(withoutHotelImage)?.image.url).toBe(eventImage.url);
    expect(proposalCover({ ...withoutHotelImage, events: [] })?.image.url).toBe(poiImage.url);
    cleanup();
    render(<TripCard proposal={typedProposal} onOpen={vi.fn()} />);
    expect(screen.getByRole("img", { name: "Отель" }).closest("figure")).toHaveClass("trip-card-cover");
  });
});
