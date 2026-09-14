"use client";

import { useCallback, useState } from "react";
import { api } from "./api";
import { useChatContext } from "./chat-context";
import { describeRating, type TasteRating } from "./taste";
import type { NextAction } from "./types";

export type RateShotArgs = {
  shotId: string;
  coffeeId: string | null;
};

// Single submit path shared by the Shots page and the in-chat artifact:
// persist the rating, then either hand it back to the live agent (which
// narrates and proposes the one change) or, offline, compute the deterministic
// recommendation to show inline.
export function useRateShot() {
  const { send } = useChatContext();
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<NextAction | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(
    async (args: RateShotArgs, rating: TasteRating) => {
      setSubmitting(true);
      setError(null);
      setResult(null);
      try {
        await api.feedback(args.shotId, rating);
        const { mode } = await api.activity();
        if (mode === "live") {
          await send(describeRating(rating, args.shotId));
        } else if (args.coffeeId) {
          setResult(await api.nextAction(args.coffeeId, rating));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not save your rating.");
      } finally {
        setSubmitting(false);
      }
    },
    [send],
  );

  return { submitting, result, error, submit };
}
