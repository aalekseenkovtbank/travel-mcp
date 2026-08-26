import type {
  AsyncJobAccepted,
  ChatMessage,
  City,
  JobEvent,
  TripBrief,
  TripBriefInterpretationRequest,
  TripBriefInterpretationResponse,
  TripDetail,
  TripMessageInput,
  TripRunSnapshot,
  SystemReadiness,
} from "@travel-growth-inspiration/contracts";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

async function json<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...init?.headers,
    },
  });
  const rawPayload = await response.text();
  if (!rawPayload.trim()) {
    throw new Error(
      response.ok
        ? "Сервис вернул пустой ответ. Попробуйте ещё раз."
        : `Сервис временно не ответил (HTTP ${response.status}). Попробуйте ещё раз.`,
    );
  }
  let payload: T & { error?: { message?: string } };
  try {
    payload = JSON.parse(rawPayload) as T & { error?: { message?: string } };
  } catch {
    throw new Error(
      response.ok
        ? "Сервис вернул неполный ответ. Попробуйте ещё раз."
        : `Сервис временно недоступен (HTTP ${response.status}). Попробуйте ещё раз.`,
    );
  }
  if (!response.ok) throw new Error(payload.error?.message ?? `HTTP ${response.status}`);
  return payload;
}

export const api = {
  cities: () => json<{ cities: City[] }>(`${API_BASE}/catalog/cities`),
  readiness: () => json<SystemReadiness>(`${API_BASE}/system/readiness`),
  interpretBrief: (input: TripBriefInterpretationRequest) =>
    json<TripBriefInterpretationResponse>(`${API_BASE}/trip-briefs/interpret`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  createRun: (brief: TripBrief) =>
    json<AsyncJobAccepted>(`${API_BASE}/trip-runs`, {
      method: "POST",
      body: JSON.stringify(brief),
    }),
  run: (runId: string) => json<TripRunSnapshot>(`${API_BASE}/trip-runs/${runId}`),
  trip: (tripId: string) => json<TripDetail>(`${API_BASE}/trips/${tripId}`),
  messages: (tripId: string) =>
    json<{ messages: ChatMessage[] }>(`${API_BASE}/trips/${tripId}/messages`),
  message: (tripId: string, input: TripMessageInput) =>
    json<AsyncJobAccepted>(`${API_BASE}/trips/${tripId}/messages`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  refresh: (tripId: string) =>
    json<AsyncJobAccepted>(`${API_BASE}/trips/${tripId}/refresh`, { method: "POST" }),
};

export function watchJob(
  jobId: string,
  onEvent: (event: JobEvent) => void,
  onConnectionError: () => void,
  afterEventId = 0,
): () => void {
  const after = afterEventId > 0 ? `?after=${afterEventId}` : "";
  const source = new EventSource(`${API_BASE}/jobs/${jobId}/events${after}`);
  const eventTypes = [
    "job.started",
    "profile.ready",
    "shortlist.ready",
    "candidate.progress",
    "trip.partial",
    "trip.ready",
    "job.completed",
    "job.failed",
  ] as const;
  for (const type of eventTypes) {
    source.addEventListener(type, (raw) => {
      const event = raw as MessageEvent<string>;
      onEvent({
        id: Number(event.lastEventId),
        jobId,
        type,
        data: JSON.parse(event.data) as Record<string, unknown>,
        createdAt: new Date().toISOString(),
      });
      if (type === "job.completed" || type === "job.failed") source.close();
    });
  }
  source.onerror = () => {
    if (source.readyState === EventSource.CLOSED) onConnectionError();
  };
  return () => source.close();
}
