"use client";

import { useState } from "react";
import { NextActionCard } from "./artifact-ui";
import { TasteBloom } from "./TasteBloom";
import { Button } from "./ui";
import { defaultRating, MAX_VALUE, MIN_VALUE, VALUE_STEP, type TasteRating } from "@/lib/taste";
import { useRateShot } from "@/lib/useRateShot";

export function RatingCard({ shotId, coffeeId }: { shotId: string | null; coffeeId: string | null }) {
  const { submitting, result, error, submit } = useRateShot();
  const [rating, setRating] = useState<TasteRating>(defaultRating);

  const ready = Boolean(shotId) && !submitting;

  return (
    <div className="my-3 w-full max-w-sm overflow-hidden rounded-2xl border border-line-soft bg-ground-2/90">
      <div className="flex items-center justify-between border-b border-line-soft px-4 py-2.5">
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-cream-faint">Taste bloom</span>
        {shotId && <span className="font-mono text-[11px] text-cream-faint">shot #{shotId}</span>}
      </div>
      <div className="px-4 py-3.5">
        <div className="aspect-square w-full max-w-[280px]">
          <TasteBloom value={rating} onChange={setRating} disabled={submitting} />
        </div>

        <label className="mt-4 flex items-center gap-3 text-sm text-cream-dim">
          <span className="w-16 shrink-0 font-mono text-xs uppercase tracking-wider text-cream-faint">Overall</span>
          <input
            type="range"
            min={MIN_VALUE}
            max={MAX_VALUE}
            step={VALUE_STEP}
            value={rating.overall}
            disabled={submitting}
            onChange={(e) => setRating((r) => ({ ...r, overall: Number(e.target.value) }))}
            className="h-1.5 flex-1 accent-crema"
            aria-label="Overall rating"
          />
          <span className="w-8 text-right font-mono text-sm text-cream">{rating.overall.toFixed(1)}</span>
        </label>

        <div className="mt-4 flex items-center gap-3">
          {shotId ? (
            <Button
              onClick={() => void submit({ shotId, coffeeId }, rating)}
              disabled={!ready}
              className="px-5"
            >
              {submitting ? "Saving…" : "Save rating"}
            </Button>
          ) : (
            <span className="text-xs text-cream-faint">No shot is attached to this rating.</span>
          )}
          {error && <span className="text-xs text-rust">{error}</span>}
        </div>

        {result && <NextActionCard action={result} />}
      </div>
    </div>
  );
}
