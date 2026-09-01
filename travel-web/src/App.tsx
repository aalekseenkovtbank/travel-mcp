import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { BrowserRouter, Link, Route, Routes, useNavigate, useParams } from "react-router-dom";
import type {
  ChatMessage,
  City,
  ImageAsset,
  JobEvent,
  SystemReadiness,
  TripBrief,
  TripDetail,
  TripIntentContext,
  TripProposal,
  TripRunSnapshot,
  WeatherDay,
} from "@travel-growth-inspiration/contracts";

import { api, watchJob } from "./api";
import { EntityImage } from "./EntityImage";
import {
  readPlannerSession,
  writePlannerSession,
  type ActivePlannerJob,
  type PlannerSession,
} from "./planner-session";
import { TripMap } from "./TripMap";
import { WeekendMoscow } from "./WeekendMoscow";

const interestOptions = ["гастрономия", "концерты", "театр", "музеи", "природа", "архитектура"];

function isoAfter(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function money(value: number): string {
  return `${Math.round(value).toLocaleString("ru-RU")} ₽`;
}

function friendlyDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short" }).format(
    new Date(`${value}T12:00:00`),
  );
}

function tripDayDate(startDate: string, day: number): string {
  const date = new Date(`${startDate}T12:00:00.000Z`);
  date.setUTCDate(date.getUTCDate() + day - 1);
  return date.toISOString().slice(0, 10);
}

function temperature(value: number): string {
  return value > 0 ? `+${value}` : String(value);
}

function weatherSymbol(code: number): string {
  if (code === 0) return "☀";
  if (code <= 3) return "☁";
  if (code === 45 || code === 48) return "≋";
  if ((code >= 71 && code <= 77) || code === 85 || code === 86) return "❄";
  if (code >= 95) return "⚡";
  return "☂";
}

function cacheableRun(run: TripRunSnapshot): TripRunSnapshot {
  const { profile: _profile, ...snapshot } = run;
  return snapshot;
}

const technicalMessagePattern = /(?:<!doctype|<html|<style|openai|gpt(?:-|\b)|api[_ -]?key|request[_ -]?id|response headers|stack trace)/iu;

function safeUserText(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const compact = value.trim().replace(/\s+/gu, " ");
  if (!compact || compact.length > 240 || technicalMessagePattern.test(compact)) return undefined;
  return compact;
}

function userError(reason: unknown, fallback: string): string {
  return safeUserText(reason instanceof Error ? reason.message : reason) ?? fallback;
}

function visibleWarnings(values: string[]): string[] {
  return [...new Set(values.map(safeUserText).filter((value): value is string => Boolean(value)))];
}

function effectiveProposalCompleteness(proposal: TripProposal): TripProposal["completeness"] {
  if (proposal.completeness === "failed") return "failed";
  return (proposal.sources ?? []).some((source) =>
    source.component !== "editorial" && source.availability === "unavailable",
  ) ? "partial" : "complete";
}

function effectiveRunCompleteness(
  run: TripRunSnapshot,
  proposals: TripProposal[],
): TripRunSnapshot["completeness"] {
  if (run.completeness !== "partial" || proposals.length !== 3) return run.completeness;
  const onlyEditorialWasUnavailable = run.sources.every((source) =>
    source.availability === "available" || source.component === "editorial",
  );
  return onlyEditorialWasUnavailable && proposals.every((proposal) =>
    effectiveProposalCompleteness(proposal) === "complete",
  ) ? "complete" : "partial";
}

function sourceView(source: TripProposal["sources"][number]): {
  availability: "available" | "unavailable";
  name: string;
  status: string;
} {
  if (source.component === "editorial") {
    return {
      availability: "available",
      name: source.availability === "unavailable" ? "Локальный редактор" : source.source,
      status: "доступен",
    };
  }
  return {
    availability: source.availability,
    name: source.source,
    status: source.availability === "available"
      ? "доступен"
      : safeUserText(source.message) ?? "временно недоступен",
  };
}

function WeatherSummary({ day }: { day: WeatherDay }) {
  const range = `${temperature(day.temperatureMinC)}…${temperature(day.temperatureMaxC)} °C`;
  if (day.kind === "forecast") {
    return (
      <div className="weather-summary forecast">
        <span className="weather-symbol" aria-hidden="true">{weatherSymbol(day.weatherCode)}</span>
        <span>{range}</span>
        <span>осадки {day.precipitationProbabilityPct}%</span>
        <em>прогноз</em>
      </div>
    );
  }
  return (
    <div
      className="weather-summary climate"
      title={`Приблизительная оценка по статистике ERA5 за 1991–2020 годы: осадки выпадали в ${day.precipitationFrequencyPct}% из ${day.sampleSize} похожих дней`}
    >
      <span className="weather-symbol" aria-hidden="true">≈</span>
      <span>{range}</span>
      <span>осадки {day.precipitationFrequencyPct}%</span>
    </div>
  );
}

function sourceComponentLabel(component: TripProposal["sources"][number]["component"]): string {
  return {
    profile: "профиль",
    flights: "перелёты",
    hotel: "отель",
    event: "события",
    nearby: "места рядом",
    weather: "погода",
    editorial: "оформление",
  }[component];
}

function tierLabel(tier: TripProposal["tier"]): string {
  return {
    economy: "Экономнее",
    balanced: "Баланс",
    comfort: "Комфорт",
    cohort_floor: "Низ когорты",
    cohort_typical: "Середина когорты",
    cohort_ceiling: "Верх когорты",
    within_budget: "В бюджете",
    closest_over_budget: "Ближе всего к бюджету",
  }[tier];
}

function Logo() {
  return (
    <Link className="logo" to="/" aria-label="Travel Nova, на главную">
      <span className="logo-mark">N</span>
      <span>travel nova</span>
    </Link>
  );
}

function TbankAction({
  url,
  label,
}: {
  url?: string;
  label: string;
}) {
  if (!url) {
    return (
      <span
        className="tbank-action is-disabled"
        aria-disabled="true"
        title="Ссылка T-Bank недоступна"
      >
        Ссылка T-Bank недоступна
      </span>
    );
  }

  return (
    <a className="tbank-action" href={url} target="_blank" rel="noopener noreferrer">
      {label}
    </a>
  );
}

function Header({ dataMode, degraded = false }: { dataMode?: "demo" | "real"; degraded?: boolean }) {
  const label = dataMode === "demo" ? "Демо-данные" : dataMode === "real" ? "Реальные данные" : "Локальная alpha";
  return (
    <header className="site-header">
      <Logo />
      <div className={`header-note ${degraded ? "degraded" : ""}`}>
        <span className="live-dot" /> {label}{degraded ? " · источники не готовы" : ""}
      </div>
    </header>
  );
}

export function proposalCover(proposal: TripProposal): { image: ImageAsset; alt: string } | undefined {
  if (proposal.hotel.image) return { image: proposal.hotel.image, alt: proposal.hotel.name };
  const event = proposal.events.find((item) => item.image);
  if (event?.image) return { image: event.image, alt: event.name };
  const point = proposal.mapPoints.find((item) => item.type === "poi" && item.image);
  return point?.image ? { image: point.image, alt: point.name } : undefined;
}

export function TripCard({
  proposal,
  onOpen,
  preparing = false,
}: {
  proposal: TripProposal;
  onOpen: () => void;
  preparing?: boolean;
}) {
  const liveCount = proposal.priceBreakdown.filter((item) => item.price.kind === "live").length;
  const cover = proposalCover(proposal);
  const completeness = effectiveProposalCompleteness(proposal);
  return (
    <article className={`trip-card ${cover ? "has-cover" : ""}`} style={{ "--accent": proposal.destination.accent } as React.CSSProperties}>
      <div className="trip-card-top">
        <span className={`tier tier-${proposal.tier}`}>{tierLabel(proposal.tier)}</span>
        <span className={`verified ${preparing ? "preparing" : completeness}`}>
          {preparing ? "дополняем маршрут" : completeness === "partial" ? "неполный вариант" : liveCount ? `${liveCount} живых цен` : "оценка"}
        </span>
      </div>
      {cover ? <EntityImage image={cover.image} alt={cover.alt} className="trip-card-cover" /> : null}
      <div className="destination-code">{proposal.destination.iata}</div>
      <h3>{proposal.title}</h3>
      <p className="tagline">{proposal.tagline}</p>
      <div className="trip-dates">
        {friendlyDate(proposal.startDate)} — {friendlyDate(proposal.endDate)}
      </div>
      <div className="card-route">
        <span>{proposal.flights.outbound.departureTime ?? "—"}</span>
        <span className="route-line" />
        <span>{proposal.destination.name}</span>
      </div>
      <div className="card-feature">
        <span>⌂</span>
        <div><strong>{proposal.hotel.name}</strong><small>{"★".repeat(proposal.hotel.stars)} {proposal.hotel.meal ?? ""}</small></div>
      </div>
      {proposal.events[0] ? (
        <div className="card-feature">
          <span>✦</span>
          <div>
            <strong>{proposal.events[0].name}</strong>
            <small>{proposal.events[0].dateTime ?? proposal.events[0].kind}{proposal.events.length > 1 ? ` · ещё ${proposal.events.length - 1}` : ""}</small>
          </div>
        </div>
      ) : null}
      <div className="card-price">
        <div><small>{preparing ? "Предварительно" : "Вся поездка"}</small><strong>{money(proposal.totalPrice.amount)}</strong></div>
        <button className="round-button" onClick={onOpen} aria-label={`Открыть ${proposal.title}`}>→</button>
      </div>
    </article>
  );
}

function PlannerPage() {
  const navigate = useNavigate();
  const [initialSession] = useState(readPlannerSession);
  const [cities, setCities] = useState<City[]>([]);
  const [readiness, setReadiness] = useState<SystemReadiness>();
  const [plannerMode, setPlannerMode] = useState<"form" | "text">(initialSession?.mode ?? "form");
  const [promptText, setPromptText] = useState(initialSession?.promptText ?? "");
  const [interpretation, setInterpretation] = useState<TripIntentContext | undefined>(
    initialSession?.interpretation ?? initialSession?.run?.brief.intent,
  );
  const [interpreting, setInterpreting] = useState(false);
  const [origin, setOrigin] = useState(initialSession?.form.origin ?? "saint-petersburg");
  const [destination, setDestination] = useState(initialSession?.form.destination ?? "");
  const [adults, setAdults] = useState(initialSession?.form.adults ?? 1);
  const [childrenAges, setChildrenAges] = useState<number[]>(initialSession?.form.childrenAges ?? []);
  const [timeMode, setTimeMode] = useState<"exact" | "flexible">(initialSession?.form.timeMode ?? "exact");
  const [startDate, setStartDate] = useState(initialSession?.form.startDate ?? isoAfter(14));
  const [endDate, setEndDate] = useState(initialSession?.form.endDate ?? isoAfter(17));
  const [windowStart, setWindowStart] = useState(initialSession?.form.windowStart ?? isoAfter(10));
  const [windowEnd, setWindowEnd] = useState(initialSession?.form.windowEnd ?? isoAfter(35));
  const [nights, setNights] = useState(initialSession?.form.nights ?? 3);
  const [budget, setBudget] = useState(initialSession?.form.budget ?? "");
  const [interests, setInterests] = useState<string[]>(initialSession?.form.interests ?? ["гастрономия"]);
  const [run, setRun] = useState<TripRunSnapshot | undefined>(initialSession?.run);
  const [proposals, setProposals] = useState<TripProposal[]>(initialSession?.proposals ?? []);
  const [progress, setProgress] = useState<string[]>(initialSession?.progress ?? []);
  const [error, setError] = useState(safeUserText(initialSession?.error) ?? "");
  const [activeJob, setActiveJob] = useState<ActivePlannerJob | undefined>(initialSession?.activeJob);
  const [loading, setLoading] = useState(Boolean(initialSession?.activeJob));
  const stopWatching = useRef<(() => void) | undefined>(undefined);
  const latestSession = useRef<PlannerSession | undefined>(undefined);

  const session = useMemo<PlannerSession>(() => ({
    version: 2,
    mode: plannerMode,
    promptText,
    ...(interpretation ? { interpretation } : {}),
    form: {
      origin,
      destination,
      adults,
      childrenAges,
      timeMode,
      startDate,
      endDate,
      windowStart,
      windowEnd,
      nights,
      budget,
      interests,
    },
    ...(run ? { run: cacheableRun(run) } : {}),
    proposals,
    progress,
    error,
    ...(activeJob ? { activeJob } : {}),
    scrollY: initialSession?.scrollY ?? 0,
  }), [
    activeJob,
    adults,
    budget,
    childrenAges,
    destination,
    endDate,
    error,
    initialSession?.scrollY,
    interpretation,
    interests,
    nights,
    origin,
    plannerMode,
    progress,
    promptText,
    proposals,
    run,
    startDate,
    timeMode,
    windowEnd,
    windowStart,
  ]);

  latestSession.current = session;

  useEffect(() => {
    writePlannerSession(session);
  }, [session]);

  useEffect(() => {
    api.cities().then(({ cities: values }) => setCities(values)).catch((reason: Error) =>
      setError(userError(reason, "Не удалось загрузить список городов")));
    api.readiness().then(setReadiness).catch(() => undefined);
  }, []);

  useEffect(() => {
    const savedScrollY = initialSession?.scrollY ?? 0;
    const frame = window.requestAnimationFrame(() => {
      if (savedScrollY > 0) window.scrollTo(0, savedScrollY);
    });
    return () => {
      window.cancelAnimationFrame(frame);
      if (latestSession.current) {
        writePlannerSession({ ...latestSession.current, scrollY: window.scrollY });
      }
    };
  }, [initialSession?.scrollY]);

  useEffect(() => {
    if (activeJob || !initialSession?.run?.id) return;
    let disposed = false;
    void api.run(initialSession.run.id).then((snapshot) => {
      if (disposed) return;
      setRun(snapshot);
      setProposals(snapshot.trips);
      if (snapshot.brief.intent) setInterpretation(snapshot.brief.intent);
    }).catch(() => undefined);
    return () => {
      disposed = true;
    };
  }, [activeJob, initialSession?.run?.id]);

  useEffect(() => {
    if (!activeJob) return;
    let disposed = false;
    const { jobId, runId, lastEventId } = activeJob;

    const applyFinishedRun = (snapshot: TripRunSnapshot) => {
      setRun(snapshot);
      setProposals(snapshot.trips);
      if (snapshot.brief.intent) setInterpretation(snapshot.brief.intent);
      setLoading(false);
      setActiveJob(undefined);
      if (snapshot.status === "completed") {
        setProgress((current) => current.at(-1) === "Все доступные варианты проверены"
          ? current
          : [...current, "Все доступные варианты проверены"]);
      } else {
        setError(userError(snapshot.warnings.at(-1), "Не удалось собрать поездки"));
      }
    };

    const loadFinishedRun = async () => {
      try {
        const snapshot = await api.run(runId);
        if (!disposed) applyFinishedRun(snapshot);
      } catch (reason) {
        if (!disposed) {
          setError(userError(reason, "Не удалось загрузить подборку"));
          setLoading(false);
        }
      }
    };

    const resume = async () => {
      try {
        const snapshot = await api.run(runId);
        if (disposed) return;
        if (["completed", "failed", "interrupted"].includes(snapshot.status)) {
          applyFinishedRun(snapshot);
          return;
        }
        stopWatching.current = watchJob(
          jobId,
          (jobEvent) => {
            if (disposed) return;
            handlePlannerEvent(jobEvent, setProgress, setProposals);
            if (jobEvent.type === "job.completed") {
              void loadFinishedRun();
              return;
            }
            if (jobEvent.type === "job.failed") {
              setError(userError(jobEvent.data.message, "Не удалось собрать поездки"));
              setLoading(false);
              setActiveJob(undefined);
              return;
            }
            setActiveJob((current) => current?.jobId === jobId
              ? { ...current, lastEventId: jobEvent.id }
              : current);
          },
          () => {
            if (!disposed) void loadFinishedRun();
          },
          lastEventId,
        );
      } catch (reason) {
        if (!disposed) {
          setError(userError(reason, "Не удалось продолжить подбор"));
          setLoading(false);
        }
      }
    };

    void resume();
    return () => {
      disposed = true;
      stopWatching.current?.();
      stopWatching.current = undefined;
    };
  }, [activeJob?.jobId, activeJob?.runId]);

  const toggleInterest = (interest: string) => {
    setInterests((current) =>
      current.includes(interest) ? current.filter((item) => item !== interest) : [...current, interest],
    );
  };

  const changeChildren = (count: number) => {
    setChildrenAges((current) =>
      Array.from({ length: count }, (_, index) => current[index] ?? 8),
    );
  };

  const prepareSubmission = (message: string) => {
    stopWatching.current?.();
    setActiveJob(undefined);
    setError("");
    setRun(undefined);
    setProposals([]);
    setProgress([message]);
    setLoading(true);
  };

  const createRun = async (brief: TripBrief) => {
    const accepted = await api.createRun(brief);
    if (!accepted.jobId || !accepted.runId) throw new Error("Сервис не вернул идентификатор подбора");
    setActiveJob({ jobId: accepted.jobId, runId: accepted.runId, lastEventId: 0 });
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    prepareSubmission("Запускаем персональный подбор");
    setInterpretation(undefined);
    const brief: TripBrief = {
      preset: "weekend",
      originCityId: origin,
      ...(destination ? { destinationCityId: destination } : {}),
      travelers: { adults, childrenAges },
      time:
        timeMode === "exact"
          ? { mode: "exact", startDate, endDate }
          : { mode: "flexible", windowStart, windowEnd, nights },
      ...(budget ? { budgetRub: Number(budget) } : {}),
      ...(interests.length ? { interests } : {}),
    };
    try {
      await createRun(brief);
    } catch (reason) {
      setError(userError(reason, "Не удалось начать подбор"));
      setLoading(false);
    }
  };

  const submitText = async (event?: FormEvent) => {
    event?.preventDefault();
    const text = promptText.trim();
    if (!text || loading) return;
    prepareSubmission("Разбираем пожелания…");
    setInterpretation(undefined);
    setInterpreting(true);
    try {
      const interpreted = await api.interpretBrief({ text, defaultOriginCityId: origin });
      setInterpretation(interpreted.interpretation);
      setOrigin(interpreted.brief.originCityId);
      setProgress(["Пожелания разобраны", "Запускаем персональный подбор"]);
      setInterpreting(false);
      await createRun(interpreted.brief);
    } catch (reason) {
      setError(userError(reason, "Не удалось разобрать описание поездки"));
      setLoading(false);
      setInterpreting(false);
    }
  };

  const runWarnings = visibleWarnings(run?.warnings ?? []);
  const runCompleteness = run ? effectiveRunCompleteness(run, proposals) : undefined;
  const llmReadiness = readiness?.sources.find((source) =>
    source.id === "llmProxy" || source.id === "openai"
  );
  const textModeUnavailable = llmReadiness !== undefined && llmReadiness.status !== "ready";

  return (
    <main>
      <Header dataMode={readiness?.dataMode} degraded={readiness?.status === "degraded"} />
      <section className="hero shell">
        <div className="eyebrow">Персональный travel-консьерж</div>
        <h1>Не ищите билеты.<br /><em>Выбирайте впечатление.</em></h1>
        <p className="hero-copy">Три готовых путешествия по России — с перелётом, отелем, событиями и местами, которые подходят именно вам.</p>
      </section>

      <section className="planner shell">
        {readiness?.status === "degraded" ? (
          <div className="notice readiness-notice">
            Реальный контур пока не готов: {readiness.sources.filter((source) => source.required && source.status !== "ready").map((source) => source.message).join(" · ")}
          </div>
        ) : null}
        <div className="segmented planner-mode" role="tablist" aria-label="Способ описания поездки">
          <button
            type="button"
            role="tab"
            aria-selected={plannerMode === "form"}
            className={plannerMode === "form" ? "active" : ""}
            onClick={() => setPlannerMode("form")}
          >
            Форма
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={plannerMode === "text"}
            className={plannerMode === "text" ? "active" : ""}
            onClick={() => setPlannerMode("text")}
          >
            Описать словами
          </button>
        </div>
        {plannerMode === "form" ? (
          <form className="brief-form" onSubmit={submit}>
          <div className="form-row two">
            <label>Откуда
              <select value={origin} onChange={(event) => setOrigin(event.target.value)}>
                {cities.map((city) => <option key={city.id} value={city.id}>{city.name} · {city.iata}</option>)}
              </select>
            </label>
            <label>Куда <span className="optional">необязательно</span>
              <select value={destination} onChange={(event) => setDestination(event.target.value)}>
                <option value="">Удивите меня</option>
                {cities.filter((city) => city.id !== origin).map((city) => <option key={city.id} value={city.id}>{city.name}</option>)}
              </select>
            </label>
          </div>

          <div className="segmented">
            <button type="button" className={timeMode === "exact" ? "active" : ""} onClick={() => setTimeMode("exact")}>Точные даты</button>
            <button type="button" className={timeMode === "flexible" ? "active" : ""} onClick={() => setTimeMode("flexible")}>Гибкий период</button>
          </div>
          {timeMode === "exact" ? (
            <div className="form-row two">
              <label>Вылет<input required type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label>
              <label>Возвращение<input required type="date" value={endDate} min={startDate} onChange={(event) => setEndDate(event.target.value)} /></label>
            </div>
          ) : (
            <div className="form-row three">
              <label>Начало окна<input required type="date" value={windowStart} onChange={(event) => setWindowStart(event.target.value)} /></label>
              <label>Конец окна<input required type="date" value={windowEnd} min={windowStart} onChange={(event) => setWindowEnd(event.target.value)} /></label>
              <label>Ночей<input required type="number" min="1" max="30" value={nights} onChange={(event) => setNights(Number(event.target.value))} /></label>
            </div>
          )}

          <div className="form-row three">
            <label>Взрослые<input type="number" min="1" max="6" value={adults} onChange={(event) => setAdults(Number(event.target.value))} /></label>
            <label>Дети<input type="number" min="0" max="5" value={childrenAges.length} onChange={(event) => changeChildren(Number(event.target.value))} /></label>
            <label>Бюджет <span className="optional">необязательно</span><div className="input-suffix"><input type="number" min="1000" step="1000" placeholder="Без лимита" value={budget} onChange={(event) => setBudget(event.target.value)} /><span>₽</span></div></label>
          </div>
          {childrenAges.length ? (
            <div className="child-ages">
              {childrenAges.map((age, index) => (
                <label key={index}>Возраст ребёнка {index + 1}<input type="number" min="0" max="17" value={age} onChange={(event) => setChildrenAges((current) => current.map((item, itemIndex) => itemIndex === index ? Number(event.target.value) : item))} /></label>
              ))}
            </div>
          ) : null}

          <div className="interest-row">
            <span>Что вам близко</span>
            <div className="chips">
              {interestOptions.map((interest) => <button type="button" key={interest} className={interests.includes(interest) ? "selected" : ""} onClick={() => toggleInterest(interest)}>{interest}</button>)}
            </div>
          </div>
          <button className="primary-action" type="submit" disabled={loading || cities.length === 0}>
            {loading ? "Собираем путешествия…" : "Показать три путешествия"}<span>→</span>
          </button>
          </form>
        ) : (
          <form className="brief-form text-brief-form" onSubmit={(event) => void submitText(event)}>
            <label className="text-brief-label" htmlFor="trip-description">
              Расскажите, какой отдых вам хочется
              <textarea
                id="trip-description"
                value={promptText}
                maxLength={4_000}
                onChange={(event) => setPromptText(event.target.value)}
                onKeyDown={(event) => {
                  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                    event.preventDefault();
                    void submitText();
                  }
                }}
                placeholder="Например: хочу активный отпуск, много гулять на природе, чтобы в августе было не жарко"
              />
              <small>Можно написать даты, компанию, бюджет, настроение или просто несколько пожеланий.</small>
            </label>
            {textModeUnavailable ? (
              <div className="notice text-mode-notice">
                Режим описания временно недоступен: {llmReadiness?.message}. Пока можно воспользоваться формой.
              </div>
            ) : null}
            <button
              className="primary-action"
              type="submit"
              disabled={loading || !promptText.trim() || textModeUnavailable}
            >
              {interpreting ? "Разбираем пожелания…" : loading ? "Собираем путешествия…" : "Поехали"}<span>→</span>
            </button>
          </form>
        )}
      </section>

      {progress.length || proposals.length || error ? (
        <section className="results shell" aria-live="polite">
          {interpretation ? (
            <div className="intent-summary">
              <div className="intent-summary-title">
                <div><div className="eyebrow">Как мы вас поняли</div><h2>{interpretation.summary}</h2></div>
              </div>
              <div className="intent-summary-groups">
                {interpretation.understood.length ? (
                  <div><strong>Поняли</strong><div>{interpretation.understood.map((item) => <span key={item}>{item}</span>)}</div></div>
                ) : null}
                {interpretation.assumptions.length ? (
                  <div><strong>Предположили</strong><div>{interpretation.assumptions.map((item) => <span key={item}>{item}</span>)}</div></div>
                ) : null}
                {interpretation.unverified.length ? (
                  <div className="unverified"><strong>Не можем проверить</strong><div>{interpretation.unverified.map((item) => <span key={item}>{item}</span>)}</div></div>
                ) : null}
              </div>
            </div>
          ) : null}
          <div className="section-heading">
            <div><div className="eyebrow">Ваша подборка</div><h2>{loading ? "Собираем маршрут по частям" : "Три способа уехать"}</h2></div>
            {loading ? <div className="spinner" /> : null}
          </div>
          {error ? <div className="notice error">{error}</div> : null}
          {runWarnings.length ? <div className="notice">{runWarnings.join(" ")}</div> : null}
          {run && runCompleteness ? <div className={`run-state ${runCompleteness}`}>{run.dataMode === "demo" ? "Демонстрационная подборка" : "Подборка на реальных данных"} · {runCompleteness === "complete" ? "все источники доступны" : runCompleteness === "partial" ? "часть необязательных данных недоступна" : "сбор не завершён"}</div> : null}
          <div className="progress-line">{progress.slice(-1)[0]}</div>
          <div className="trip-grid">
            {proposals.map((proposal) => (
              <TripCard
                key={proposal.id}
                proposal={proposal}
                preparing={loading && !proposal.sources.some((source) => source.component === "editorial")}
                onOpen={() => navigate(`/trips/${proposal.id}`)}
              />
            ))}
            {loading ? Array.from({ length: Math.max(0, 3 - proposals.length) }, (_, index) => <div key={index} className="trip-card skeleton" />) : null}
          </div>
        </section>
      ) : null}
      <footer className="shell">Travel Nova проверяет данные, но не бронирует и не списывает деньги.</footer>
    </main>
  );
}

function handlePlannerEvent(
  event: JobEvent,
  setProgress: React.Dispatch<React.SetStateAction<string[]>>,
  setProposals: React.Dispatch<React.SetStateAction<TripProposal[]>>,
) {
  const messages: Partial<Record<JobEvent["type"], string>> = {
    "job.started": "Изучаем параметры поездки",
    "profile.ready": "Персональный профиль готов",
    "shortlist.ready": "Выбрали города-кандидаты",
    "trip.partial": "Рейсы и отель готовы; дополняем маршрут",
    "trip.ready": "Готовый вариант сохранён",
    "job.completed": "Все доступные варианты проверены",
  };
  const message = event.type === "candidate.progress"
    ? `${event.data.cityName}: ${event.data.status}`
    : messages[event.type];
  if (message) setProgress((current) => [...current, message]);
  if (event.type === "trip.partial" || event.type === "trip.ready") {
    const proposal = event.data.proposal as TripProposal | undefined;
    if (proposal) setProposals((current) => [...current.filter((item) => item.id !== proposal.id), proposal]);
  }
}

function TripPage() {
  const { tripId = "" } = useParams();
  const [trip, setTrip] = useState<TripDetail>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [activeRestaurantGroupId, setActiveRestaurantGroupId] = useState("");
  const stopWatching = useRef<(() => void) | undefined>(undefined);

  const load = async () => {
    const [tripValue, messageValue] = await Promise.all([api.trip(tripId), api.messages(tripId)]);
    setTrip(tripValue);
    setMessages(messageValue.messages);
  };

  useEffect(() => {
    window.scrollTo(0, 0);
    void load().catch((reason: Error) => setError(userError(reason, "Не удалось открыть поездку")));
    return () => stopWatching.current?.();
  }, [tripId]);

  useEffect(() => {
    if (trip?.preparationStatus !== "preparing") return;
    let disposed = false;
    let timer: number | undefined;
    const poll = async () => {
      try {
        const value = await api.trip(tripId);
        if (disposed) return;
        setTrip(value);
        setError("");
        if (value.preparationStatus === "preparing") {
          timer = window.setTimeout(() => void poll(), 2_000);
        }
      } catch (reason) {
        if (disposed) return;
        setError(userError(reason, "Не удалось проверить готовность поездки"));
        timer = window.setTimeout(() => void poll(), 4_000);
      }
    };
    timer = window.setTimeout(() => void poll(), 2_000);
    return () => {
      disposed = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [tripId, trip?.preparationStatus]);

  const proposal = trip?.latestRevision.proposal;
  const preparationStatus = trip?.preparationStatus ?? "ready";
  const preparing = preparationStatus === "preparing";
  const preparationFailed = preparationStatus === "failed";
  const preparationLocked = preparationStatus !== "ready";
  const activeRestaurantGroup = proposal?.restaurantGroups.find((group) =>
    group.id === activeRestaurantGroupId,
  ) ?? proposal?.restaurantGroups[0];
  const visibleMapPoints = useMemo(() => {
    if (!proposal) return [];
    const base = proposal.mapPoints.filter((point) => point.type !== "restaurant");
    const restaurants = activeRestaurantGroup?.restaurants.map((restaurant) => restaurant.mapPoint) ?? [];
    const anchor = base.find((point) => point.id === activeRestaurantGroup?.anchorMapPointId);
    const ordered = [...(anchor ? [anchor] : []), ...base.filter((point) => point.id !== anchor?.id), ...restaurants];
    return [...new Map(ordered.map((point) => [point.id, point])).values()];
  }, [proposal, activeRestaurantGroup]);
  const personalizedRestaurants = proposal?.sources.some((source) =>
    source.component === "profile" && source.availability === "available",
  ) ?? false;
  const stale = useMemo(
    () => proposal?.priceBreakdown.some((item) => item.price.expiresAt && Date.parse(item.price.expiresAt) < Date.now()) ?? false,
    [proposal],
  );
  const itineraryDays = useMemo(() => {
    if (!proposal) return [];
    const grouped = new Map<number, TripProposal["itinerary"]>();
    for (const item of proposal.itinerary) {
      const items = grouped.get(item.day) ?? [];
      items.push(item);
      grouped.set(item.day, items);
    }
    return [...grouped.entries()]
      .sort(([left], [right]) => left - right)
      .map(([day, items]) => ({ day, items }));
  }, [proposal]);
  const weatherByDate = useMemo(
    () => new Map((proposal?.weather?.days ?? []).map((day) => [day.date, day])),
    [proposal],
  );
  const pointsWithImages = useMemo(
    () => proposal?.mapPoints.filter((point) => point.type === "poi" && point.image) ?? [],
    [proposal],
  );
  const proposalCompleteness = proposal ? effectiveProposalCompleteness(proposal) : "failed";
  const proposalWarnings = proposal ? visibleWarnings(proposal.warnings) : [];

  useEffect(() => {
    if (!proposal?.restaurantGroups.length) {
      setActiveRestaurantGroupId("");
      return;
    }
    if (!proposal.restaurantGroups.some((group) => group.id === activeRestaurantGroupId)) {
      setActiveRestaurantGroupId(proposal.restaurantGroups[0]!.id);
    }
  }, [proposal, activeRestaurantGroupId]);

  const watchMutation = (jobId: string) => {
    stopWatching.current?.();
    stopWatching.current = watchJob(
      jobId,
      (event) => {
        if (event.type === "trip.ready") {
          const proposal = event.data.proposal as TripProposal | undefined;
          const revision = event.data.revision as TripDetail["latestRevision"] | undefined;
          if (proposal || revision) {
            setTrip((current) => {
              if (!current) return current;
              const latestRevision = revision ?? {
                ...current.latestRevision,
                proposal: proposal ?? current.latestRevision.proposal,
              };
              return {
                ...current,
                latestRevision,
                revisionCount: Math.max(current.revisionCount, latestRevision.revision),
              };
            });
            setBusy(false);
            void api.messages(tripId)
              .then((value) => setMessages(value.messages))
              .catch(() => undefined);
          }
        }
        if (event.type === "job.completed" || event.type === "job.failed") {
          void load().finally(() => setBusy(false));
          if (event.type === "job.failed") setError(userError(event.data.message, "Не удалось обновить поездку"));
        }
      },
      () => setBusy(false),
    );
  };

  const send = async (value = text) => {
    if (!value.trim() || !trip || busy || preparationLocked) return;
    setBusy(true);
    setError("");
    setText("");
    try {
      const accepted = await api.message(tripId, { text: value.trim(), baseRevisionId: trip.latestRevision.id });
      const currentMessages = await api.messages(tripId);
      setMessages(currentMessages.messages);
      watchMutation(accepted.jobId);
    } catch (reason) {
      setError(userError(reason, "Не удалось отправить сообщение"));
      setBusy(false);
    }
  };

  const refresh = async () => {
    if (preparationLocked) return;
    setBusy(true);
    setError("");
    try {
      const accepted = await api.refresh(tripId);
      watchMutation(accepted.jobId);
    } catch (reason) {
      setError(userError(reason, "Не удалось обновить цены"));
      setBusy(false);
    }
  };

  if (!proposal || !trip) {
    return <main><Header /><div className="loading-page">{error || "Открываем поездку…"}</div></main>;
  }

  return (
    <main className="detail-page">
      <Header dataMode={proposal.dataMode} />
      <div className="detail-shell shell">
        <Link className="back-link" to="/">← Все варианты</Link>
        {preparing ? (
          <div className="notice">
            Маршрут уже можно смотреть. Добавляем события, места рядом и погоду — страница обновится автоматически.
          </div>
        ) : null}
        {preparationFailed ? (
          <div className="notice error">
            Не удалось дополнить маршрут, но найденные рейсы и отель сохранены. <Link to="/">Повторить подбор</Link>
          </div>
        ) : null}
        <section className="detail-hero">
          <div>
            <span className={`tier tier-${proposal.tier}`}>{tierLabel(proposal.tier)}</span>
            <h1>{proposal.title}</h1>
            <p>{proposal.tagline}</p>
            <div className="detail-meta">
              <span>{friendlyDate(proposal.startDate)} — {friendlyDate(proposal.endDate)}</span>
              <span>{proposal.travelers.adults + proposal.travelers.childrenAges.length} чел.</span>
              <span>версия {trip.revisionCount}</span>
            </div>
          </div>
          <div className="total-panel"><small>{preparing ? "Предварительный ориентир" : "Ориентир на поездку"}</small><strong>{money(proposal.totalPrice.amount)}</strong><span>{money(proposal.liveSubtotalRub)} проверено · {money(proposal.estimatedSubtotalRub)} оценка</span></div>
        </section>

        {stale ? <div className="notice">Цены проверялись больше 15 минут назад. <button onClick={refresh} disabled={busy}>Обновить</button></div> : null}
        {trip.latestRevision.changeSummary?.length ? <div className="notice revision-note"><strong>Что изменилось в версии {trip.latestRevision.revision}:</strong> {trip.latestRevision.changeSummary.join(" · ")}</div> : null}
        {proposalCompleteness === "partial" ? <div className="notice">Поездка собрана на реальных обязательных данных, но часть необязательных источников недоступна.</div> : null}
        {error ? <div className="notice error">{error}</div> : null}

        <div className="detail-layout">
          <div className="detail-main">
            <section className="panel route-panel">
              <div className="panel-title"><span>01</span><h2>Дорога и дом</h2></div>
              <div className="flight-row"><span>{proposal.flights.outbound.departureTime ?? "—"}</span><div><strong>{proposal.flights.outbound.fromCode} → {proposal.flights.outbound.toCode}</strong><small>{proposal.flights.outbound.summary}</small></div><b>{money(proposal.flights.outbound.price.amount)}</b><TbankAction url={proposal.flights.outbound.tbankUrl} label="Открыть билет в T-Bank" /></div>
              <div className="flight-row"><span>{proposal.flights.return.departureTime ?? "—"}</span><div><strong>{proposal.flights.return.fromCode} → {proposal.flights.return.toCode}</strong><small>{proposal.flights.return.summary}</small></div><b>{money(proposal.flights.return.price.amount)}</b><TbankAction url={proposal.flights.return.tbankUrl} label="Открыть билет в T-Bank" /></div>
              <div className="hotel-row">
                <div className="hotel-media">
                  <div className="hotel-symbol">⌂</div>
                  <EntityImage image={proposal.hotel.image} alt={proposal.hotel.name} className="hotel-photo" />
                </div>
                <div><strong>{proposal.hotel.name}</strong><small>{"★".repeat(proposal.hotel.stars)} {proposal.hotel.address ?? ""}</small></div>
                <b>{money(proposal.hotel.price.amount)}</b>
                <TbankAction url={proposal.hotel.tbankUrl} label="Открыть отель в T-Bank" />
              </div>
            </section>

            <section className="panel">
              <div className="panel-title"><span>02</span><h2>Программа</h2></div>
              {proposal.events.length ? (
                <div className="event-media-grid">
                  {proposal.events.map((event) => (
                    <article className={`event-media-card ${event.image ? "has-image" : ""}`} key={event.eventId}>
                      <EntityImage image={event.image} alt={event.name} className="event-photo" />
                      <div>
                        <small>{event.kind}{event.ageRestriction ? ` · ${event.ageRestriction}` : ""}{event.dateTime ? ` · ${new Date(event.dateTime).toLocaleString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}` : ""}</small>
                        <strong>{event.name}</strong>
                        {event.venue ? <span>{event.venue}</span> : null}
                        <TbankAction url={event.tbankUrl} label="Открыть событие в T-Bank" />
                      </div>
                    </article>
                  ))}
                </div>
              ) : null}
              {proposal.weather?.days.length ? null : (
                <div className="timeline-weather-empty">{preparing ? "Добавляем погоду и программу поездки…" : "Погода для дат поездки пока недоступна."}</div>
              )}
              <div className="timeline-days">
                {itineraryDays.map(({ day, items }) => {
                  const date = tripDayDate(proposal.startDate, day);
                  const weather = weatherByDate.get(date);
                  return (
                    <section className="timeline-day" key={day}>
                      <div className="timeline-day-header">
                        <div className="timeline-day-date"><span>День {day}</span><strong>{friendlyDate(date)}</strong></div>
                        {weather ? <WeatherSummary day={weather} /> : <span className="weather-unavailable">Погода для этого дня пока недоступна</span>}
                      </div>
                      <div className="timeline-day-items">
                        {items.map((item) => (
                          <div className="timeline-item" key={item.id}>
                            <div className="timeline-time">{item.time}</div>
                            <div><strong>{item.title}</strong><p>{item.description}</p></div>
                          </div>
                        ))}
                      </div>
                    </section>
                  );
                })}
              </div>
              {pointsWithImages.length ? (
                <div className="poi-gallery">
                  <h3>Что посмотреть рядом</h3>
                  <div className="poi-grid">
                    {pointsWithImages.map((point) => (
                      <article className="poi-card" key={point.id}>
                        <EntityImage image={point.image} alt={point.name} className="poi-photo" />
                        <div><strong>{point.name}</strong>{point.subtitle ? <small>{point.subtitle}</small> : null}</div>
                      </article>
                    ))}
                  </div>
                </div>
              ) : null}
            </section>

            <section className="panel">
              <div className="panel-title restaurant-title">
                <span>03</span>
                <div>
                  <h2>Где поесть</h2>
                  <small>{personalizedRestaurants ? "Учитываем ваши ресторанные предпочтения по операциям" : "Подбор по интересам и расстоянию — банковский профиль недоступен"}</small>
                </div>
              </div>
              {proposal.restaurantGroups.length ? (
                <>
                  <div className="restaurant-tabs" role="tablist" aria-label="Рестораны рядом">
                    {proposal.restaurantGroups.map((group) => (
                      <button
                        key={group.id}
                        className={group.id === activeRestaurantGroup?.id ? "active" : ""}
                        onClick={() => setActiveRestaurantGroupId(group.id)}
                        role="tab"
                        aria-selected={group.id === activeRestaurantGroup?.id}
                      >
                        {group.anchorType === "hotel" ? "Рядом с отелем" : `Рядом с: ${group.anchorName}`}
                      </button>
                    ))}
                  </div>
                  {activeRestaurantGroup?.restaurants.length ? (
                    <div className="restaurant-grid">
                      {activeRestaurantGroup.restaurants.map((restaurant) => (
                        <article className="restaurant-card" key={restaurant.osmId}>
                          <div className="restaurant-card-head">
                            <strong>{restaurant.name}</strong>
                            <div className="restaurant-card-metrics">
                              {restaurant.rating !== undefined ? (
                                <span className="restaurant-rating">
                                  ★ {restaurant.rating.toFixed(1)}
                                  {restaurant.reviewCount ? ` · ${restaurant.reviewCount.toLocaleString("ru-RU")}` : ""}
                                </span>
                              ) : null}
                              <span>≈ {restaurant.distanceMeters} м</span>
                            </div>
                          </div>
                          {restaurant.address ? <small className="restaurant-address">{restaurant.address}</small> : null}
                          <p>{restaurant.cuisine ? `Кухня: ${restaurant.cuisine}` : "Кухня не указана"}</p>
                          <small>{restaurant.openingHours ? `Часы: ${restaurant.openingHours}` : "Часы работы не указаны"}</small>
                          {restaurant.averageCheck || restaurant.delivery || restaurant.attributes?.length ? (
                            <div className="restaurant-attributes">
                              {restaurant.averageCheck ? <span>{restaurant.averageCheck}</span> : null}
                              {restaurant.delivery ? <span>Есть доставка</span> : null}
                              {restaurant.attributes?.slice(0, 3).map((attribute) => <span key={attribute}>{attribute}</span>)}
                            </div>
                          ) : null}
                          <ul>{restaurant.matchReasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                          <div className="restaurant-source">
                            {restaurant.sourceUrl ? (
                              <a href={restaurant.sourceUrl} target="_blank" rel="noreferrer">
                                Данные: {restaurant.availability.source} ↗
                              </a>
                            ) : restaurant.availability.source}
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : <div className="restaurant-empty">{safeUserText(activeRestaurantGroup?.availability.message) ?? "Рестораны рядом не найдены"}</div>}
                </>
              ) : <div className="restaurant-empty">{preparing ? "Подбираем рестораны рядом…" : "Ресторанные рекомендации пока недоступны."}</div>}
            </section>

            <section className="panel">
              <div className="panel-title"><span>04</span><h2>На карте</h2></div>
              <TripMap key={activeRestaurantGroup?.id ?? "trip-map"} points={visibleMapPoints} />
              <div className="map-legend"><span><i className="hotel" />Отель</span><span><i className="restaurant" />Еда</span><span><i className="event" />События</span><span><i className="poi" />Места</span></div>
            </section>

            <section className="panel">
              <div className="panel-title"><span>05</span><h2>Из чего сложилась цена</h2></div>
              <div className="price-list">
                {proposal.priceBreakdown.map((item) => <div key={item.label}><span>{item.label}<small className={item.price.kind}>{item.price.kind === "live" ? "живая цена" : "оценка"} · {item.price.source} · {new Date(item.price.checkedAt).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}</small></span><strong>{money(item.price.amount)}</strong></div>)}
              </div>
            </section>

            <section className="panel">
              <div className="panel-title"><span>06</span><h2>Источники данных</h2></div>
              <div className="source-list">
                {proposal.sources.map((source) => {
                  const view = sourceView(source);
                  return <div key={source.component}><span className={`source-dot ${view.availability}`} /><div><strong>{sourceComponentLabel(source.component)}</strong><small>{view.name} · {view.status}{source.component === "weather" ? ` · проверено ${new Date(source.checkedAt).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}` : ""}</small></div></div>;
                })}
              </div>
            </section>
          </div>

          <aside className="chat-panel">
            <div className="chat-header"><div><span className="live-dot" /><strong>Настроить поездку</strong></div><small>Я перепроверю изменённые части</small></div>
            <div className="quick-actions">
              {["Сделай дешевле", "Другой отель", "Другой рейс", "Другие события", "Другие рестораны"].map((action) => <button key={action} disabled={busy || preparationLocked} onClick={() => void send(action)}>{action}</button>)}
            </div>
            <div className="messages">
              {messages.length === 0 ? <div className="assistant-intro">{preparing ? "Сначала закончим дополнять маршрут — затем здесь можно будет изменить любую его часть." : "Расскажите, что изменить. Например: «хочу вылет позже» или «добавь больше локальной кухни»."}</div> : null}
              {messages.map((message) => (
                <div key={message.id} className={`message ${message.role}`}>
                  <div>{message.content}</div>
                  {message.actions?.length ? (
                    <div className="message-actions">
                      {message.actions.map((action) => (
                        <a
                          key={`${action.entityType}:${action.entityId}:${action.url}`}
                          href={action.url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {action.label}
                        </a>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
              {busy ? <div className="message assistant typing">Пересобираю и проверяю<span>…</span></div> : null}
            </div>
            <form className="chat-form" onSubmit={(event) => { event.preventDefault(); void send(); }}>
              <textarea value={text} onChange={(event) => setText(event.target.value)} placeholder="Что изменить в поездке?" rows={3} disabled={busy || preparationLocked} />
              <button type="submit" disabled={busy || preparationLocked || !text.trim()}>→</button>
            </form>
            <button className="refresh-button" onClick={refresh} disabled={busy || preparationLocked}>↻ Перепроверить все цены</button>
          </aside>
        </div>

        {proposalWarnings.length ? <section className="warnings"><strong>Важно знать</strong>{proposalWarnings.map((warning) => <p key={warning}>{warning}</p>)}</section> : null}
      </div>
    </main>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PlannerPage />} />
        <Route path="/trips/:tripId" element={<TripPage />} />
        <Route path="/weekend-moscow" element={<WeekendMoscow />} />
      </Routes>
    </BrowserRouter>
  );
}
