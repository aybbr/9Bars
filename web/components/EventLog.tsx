"use client";

import { useEffect, useState } from "react";
import { BrewDot } from "./motifs";

type LogEntry = { id: number; type: string; payload: string; at: string };

export function EventLog() {
  const [entries, setEntries] = useState<LogEntry[]>([]);

  useEffect(() => {
    const source = new EventSource("/api/events/stream");
    let id = 0;
    source.onmessage = (e) => {
      try {
        const raw = JSON.parse(e.data) as { type: string; data: unknown };
        setEntries((prev) =>
          [...prev, { id: id++, type: raw.type, payload: JSON.stringify(raw.data), at: new Date().toLocaleTimeString() }].slice(
            -200,
          ),
        );
      } catch {
        /* ignore malformed frames */
      }
    };
    return () => source.close();
  }, []);

  return (
    <div className="space-y-2">
      {entries.length === 0 ? (
        <p className="py-10 text-center text-sm text-cream-faint">Waiting for events…</p>
      ) : (
        entries.map((entry) => (
          <div key={entry.id} className="flex items-start gap-3 rounded-xl border border-line-soft bg-ground-2/70 px-3 py-2">
            <BrewDot tone="copper" className="mt-1" />
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-mono text-xs text-cream">{entry.type}</span>
                <span className="font-mono text-[11px] text-cream-faint">{entry.at}</span>
              </div>
              <p className="mt-0.5 truncate text-xs text-cream-dim">{entry.payload}</p>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
