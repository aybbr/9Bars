import type { Coffee, NextAction, ShotSummary, Span, TasteFeedback, Telemetry } from "./types";
import type { TasteRating } from "./taste";

const BASE = "";

type TasteRatingInput = TasteRating & { note?: string | null };

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  listCoffees: () => get<Coffee[]>("/api/coffee"),
  coffeeShots: (coffeeId: string) => get<ShotSummary[]>(`/api/coffee/${coffeeId}/shots`),
  telemetry: (shotId: string) => get<Telemetry>(`/api/shot/${shotId}/telemetry`),
  activity: () => get<{ spans: Span[]; mode: "live" | "demo" }>("/api/agent/activity"),
  demoLoad: () => post<{ coffee_id: string; shots: string[] }>("/api/demo/load"),
  draft: (draft: Record<string, unknown>) => post<{ draft_id: string }>("/api/draft", draft),
  approve: (draftId: string) => post<Record<string, unknown>>(`/api/draft/${draftId}/approve`, { user_confirmed: true }),
  feedback: (shotId: string, rating: TasteRatingInput) =>
    post<TasteFeedback>("/api/feedback", { shot_id: shotId, ...rating }),
  nextAction: (coffeeId: string, rating: TasteRating) =>
    post<NextAction>("/api/next-action", {
      coffee_id: coffeeId,
      acidity: rating.acidity,
      sweetness: rating.sweetness,
      body: rating.body,
      overall: rating.overall,
    }),
  shotFeedback: (shotId: string) => get<TasteFeedback>(`/api/shot/${shotId}/feedback`),
};
