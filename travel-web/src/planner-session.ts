import type { TripIntentContext, TripProposal, TripRunSnapshot } from "@travel-growth-inspiration/contracts";

export const PLANNER_SESSION_KEY = "travel-nova.planner-session.v1";

export type PlannerFormState = {
  origin: string;
  destination: string;
  adults: number;
  childrenAges: number[];
  timeMode: "exact" | "flexible";
  startDate: string;
  endDate: string;
  windowStart: string;
  windowEnd: string;
  nights: number;
  budget: string;
  interests: string[];
};

export type ActivePlannerJob = {
  jobId: string;
  runId: string;
  lastEventId: number;
};

export type PlannerSession = {
  version: 2;
  mode: "form" | "text";
  promptText: string;
  interpretation?: TripIntentContext;
  form: PlannerFormState;
  run?: TripRunSnapshot;
  proposals: TripProposal[];
  progress: string[];
  error: string;
  activeJob?: ActivePlannerJob;
  scrollY: number;
};

export function readPlannerSession(): PlannerSession | undefined {
  try {
    const raw = window.sessionStorage.getItem(PLANNER_SESSION_KEY);
    if (!raw) return undefined;
    const value = JSON.parse(raw) as Omit<Partial<PlannerSession>, "version"> & { version?: number };
    if (
      ![1, 2].includes(Number(value.version)) ||
      !value.form ||
      !Array.isArray(value.proposals) ||
      !Array.isArray(value.progress)
    ) {
      return undefined;
    }
    if (value.version === 1) {
      return {
        ...(value as Omit<PlannerSession, "version" | "mode" | "promptText">),
        version: 2,
        mode: "form",
        promptText: "",
      };
    }
    return value as PlannerSession;
  } catch {
    return undefined;
  }
}

export function writePlannerSession(value: PlannerSession): void {
  try {
    window.sessionStorage.setItem(PLANNER_SESSION_KEY, JSON.stringify(value));
  } catch {
    // The planner still works if storage is unavailable or its quota is exhausted.
  }
}
