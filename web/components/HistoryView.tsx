"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ShotSummary, Telemetry } from "@/lib/types";
import { ComparisonReport } from "./ComparisonReport";
import { RatingCard } from "./RatingCard";
import { PressureGauge, ShotChart } from "./ShotChart";
import { BrewingSpinner } from "./motifs";
import { Button, Card, MonoStat } from "./ui";

export function HistoryView() {
  const [shots, setShots] = useState<ShotSummary[]>([]);
  const [telemetry, setTelemetry] = useState<Record<string, Telemetry>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const loaded = await api.demoLoad();
        const summaries = await api.coffeeShots(loaded.coffee_id);
        if (!active) return;
        setShots(summaries);
        const map: Record<string, Telemetry> = {};
        for (const shot of summaries) {
          try {
            map[shot.shot_id] = await api.telemetry(shot.shot_id);
          } catch {
            /* skip missing telemetry */
          }
        }
        if (active) setTelemetry(map);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-cream-dim">
        <BrewingSpinner />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <h1 className="font-display text-3xl text-cream">Shots</h1>
      <p className="mt-1 text-sm text-cream-dim">
        {shots[0]?.machine_ref ? `${shots[0].machine_ref} · ` : ""}every shot, measured.
      </p>

      {shots.length >= 2 && telemetry[shots[0].shot_id] && telemetry[shots[1].shot_id] && (
        <Card className="mt-6 p-5">
          <h2 className="font-display text-lg text-cream">
            Shot #{shots[0].shot_id} vs #{shots[1].shot_id}
          </h2>
          <p className="mb-2 text-xs text-cream-dim">The corrected pull tightens the pressure curve.</p>
          <ComparisonReport first={telemetry[shots[0].shot_id]} second={telemetry[shots[1].shot_id]} />
        </Card>
      )}

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {shots.map((shot) => (
          <ShotCard key={shot.shot_id} summary={shot} telemetry={telemetry[shot.shot_id]} />
        ))}
      </div>
    </div>
  );
}

function ShotCard({ summary, telemetry }: { summary: ShotSummary; telemetry?: Telemetry }) {
  const [rating, setRating] = useState(false);
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-mono text-sm uppercase tracking-wider text-cream-faint">shot</h3>
          <p className="font-display text-xl text-cream">#{summary.shot_id}</p>
        </div>
        <PressureGauge value={summary.peak_pressure_bar} />
      </div>
      <div className="mt-3 grid grid-cols-4 gap-3 border-t border-line-soft pt-3">
        <MonoStat label="Yield" value={String(summary.dose_out_g)} unit="g" />
        <MonoStat label="Ratio" value={`1:${summary.brew_ratio.toFixed(1)}`} />
        <MonoStat label="Time" value={summary.duration_s.toFixed(1)} unit="s" />
        <MonoStat label="Temp" value={String(summary.avg_temp_c)} unit="°C" />
      </div>
      {telemetry && (
        <div className="mt-3">
          <ShotChart telemetry={telemetry} height={190} />
        </div>
      )}
      <div className="mt-4">
        <Button variant="outline" onClick={() => setRating((open) => !open)} className="px-4 py-1.5 text-xs">
          {rating ? "Close" : "Rate this shot"}
        </Button>
        {rating && (
          <div className="mt-3">
            <RatingCard shotId={summary.shot_id} coffeeId={summary.coffee_id} />
          </div>
        )}
      </div>
    </Card>
  );
}
