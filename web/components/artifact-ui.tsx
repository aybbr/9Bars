"use client";

import type { NextAction } from "@/lib/types";

export function Shell({ title, eyebrow, children }: { title: string; eyebrow: string; children: React.ReactNode }) {
  return (
    <div className="my-3 w-full max-w-2xl animate-rise overflow-hidden rounded-2xl border border-line-soft bg-ground-2/90">
      <div className="flex items-center justify-between border-b border-line-soft px-4 py-2.5">
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-cream-faint">{eyebrow}</span>
      </div>
      <div className="px-4 py-3.5">
        <h3 className="font-display text-lg text-cream">{title}</h3>
        {children}
      </div>
    </div>
  );
}

export function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function NextActionCard({ action }: { action: NextAction }) {
  return (
    <Shell eyebrow="One change · next pull" title={titleCase(action.changed_variable)}>
      <div className="mt-3 flex items-baseline gap-3 font-mono text-sm">
        <span className="text-cream-faint">{String(action.current_value)}</span>
        <span className="text-crema">→</span>
        <span className="text-crema-soft">{String(action.proposed_value)}</span>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-cream-dim">{action.rationale}</p>
      <div className="mt-3 flex items-center gap-2">
        <div className="h-1 w-24 overflow-hidden rounded-full bg-ground-4">
          <div className="h-full rounded-full bg-crema" style={{ width: `${Math.round(action.confidence * 100)}%` }} />
        </div>
        <span className="font-mono text-xs text-cream-faint">{Math.round(action.confidence * 100)}% confidence</span>
      </div>
    </Shell>
  );
}
