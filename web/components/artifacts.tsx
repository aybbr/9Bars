"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Analysis, Artifact, Coffee, DraftInput, History } from "@/lib/types";
import { NextActionCard, Shell } from "./artifact-ui";
import { RatingCard } from "./RatingCard";
import { Badge, Button, MonoStat } from "./ui";

export function ArtifactBlock({ artifact }: { artifact: Artifact }) {
  switch (artifact.kind) {
    case "research_coffee":
      return <EvidenceLedger coffee={artifact.output} />;
    case "draft_profile":
      return <ProfileDraftCard draftId={artifact.output.draft_id} input={artifact.input} />;
    case "propose_next_action":
      return <NextActionCard action={artifact.output} />;
    case "analyze_shot":
      return <AnalysisNote analysis={artifact.output} />;
    case "lookup_history":
      return <HistoryBlock history={artifact.output} />;
    case "rate_shot":
      return <RatingCard shotId={artifact.input.shot_id} coffeeId={artifact.input.coffee_id} />;
  }
}

function EvidenceLedger({ coffee }: { coffee: Coffee }) {
  const facts = coffee.evidence.filter((e) => e.source !== "inferred");
  return (
    <Shell eyebrow="Research" title={coffee.name}>
      <p className="mt-0.5 text-sm text-cream-dim">{coffee.roaster ?? "Roaster unknown"}</p>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
        <Fact label="Origin" value={coffee.origin} />
        <Fact label="Process" value={coffee.process} />
        <Fact label="Roast" value={coffee.roast_level} />
        <Fact label="Roast date" value={coffee.roast_date} />
      </dl>
      {coffee.tasting_notes.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {coffee.tasting_notes.map((note) => (
            <Badge key={note} tone="neutral">
              {note}
            </Badge>
          ))}
        </div>
      )}
      {facts.length > 0 ? (
        <ul className="mt-3 space-y-1.5">
          {facts.map((f, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-cream-dim">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-crema" />
              <span>
                {f.text}
                {f.url && (
                  <a href={f.url} target="_blank" rel="noreferrer" className="ml-1.5 font-mono text-copper hover:underline">
                    source ↗
                  </a>
                )}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-xs text-cream-faint">No sourced facts — this coffee has not been researched yet.</p>
      )}
    </Shell>
  );
}

function Fact({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-wider text-cream-faint">{label}</dt>
      <dd className="text-sm text-cream">{value ?? "—"}</dd>
    </div>
  );
}

function ProfileDraftCard({ draftId, input }: { draftId: string; input: DraftInput }) {
  const [state, setState] = useState<"idle" | "approving" | "deployed" | "rejected" | "error">("idle");
  const ratio = input.dose_g > 0 ? input.yield_g / input.dose_g : 0;

  async function approve() {
    setState("approving");
    try {
      await api.approve(draftId);
      setState("deployed");
    } catch {
      setState("error");
    }
  }

  return (
    <Shell eyebrow="Profile draft" title={input.name}>
      <div className="mt-3 grid grid-cols-3 gap-3 sm:grid-cols-5">
        <MonoStat label="Dose" value={String(input.dose_g)} unit="g" />
        <MonoStat label="Yield" value={String(input.yield_g)} unit="g" />
        <MonoStat label="Ratio" value={ratio.toFixed(1)} />
        <MonoStat label="Temp" value={String(input.temp_c)} unit="°C" />
        <MonoStat label="Grind" value={input.grind_desc} />
      </div>
      <p className="mt-3 text-sm leading-relaxed text-cream-dim">{input.rationale}</p>
      {state === "deployed" ? (
        <div className="mt-4 flex items-center gap-2 rounded-xl border border-olive/30 bg-olive/10 px-3 py-2 text-sm text-olive">
          <CheckIcon /> Approved and deployed to the machine.
        </div>
      ) : state === "rejected" ? (
        <div className="mt-4 rounded-xl border border-line bg-ground-3 px-3 py-2 text-sm text-cream-dim">Draft rejected.</div>
      ) : (
        <div className="mt-4 flex items-center gap-2">
          <Button onClick={approve} disabled={state === "approving"} className="px-5">
            {state === "approving" ? "Deploying…" : "Approve & upload"}
          </Button>
          <Button variant="ghost" onClick={() => setState("rejected")}>
            Reject
          </Button>
          {state === "error" && <span className="text-xs text-rust">Upload failed.</span>}
        </div>
      )}
    </Shell>
  );
}

function AnalysisNote({ analysis }: { analysis: Analysis }) {
  const unconfirmed = analysis.channeling_strength === "unconfirmed";
  return (
    <Shell eyebrow={`Shot #${analysis.shot_id} · analysis`} title="Telemetry reading">
      <p className="mt-2 text-sm leading-relaxed text-cream-dim">{analysis.channeling_explanation}</p>
      <div className="mt-3 flex items-center gap-2">
        <Badge tone={unconfirmed ? "olive" : "crema"}>{analysis.channeling_strength}</Badge>
        <span className="font-mono text-xs text-cream-faint">
          flow deviation {analysis.flow_deviation >= 0 ? "+" : ""}
          {analysis.flow_deviation.toFixed(2)} g/s
        </span>
      </div>
    </Shell>
  );
}

function HistoryBlock({ history }: { history: History }) {
  return (
    <Shell eyebrow="Journal" title="What we know so far">
      <table className="mt-3 w-full text-sm">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-wider text-cream-faint">
            <th className="py-1.5 font-medium">Shot</th>
            <th className="py-1.5 font-medium">Ratio</th>
            <th className="py-1.5 font-medium">Time</th>
            <th className="py-1.5 font-medium">Peak</th>
          </tr>
        </thead>
        <tbody>
          {history.shots.map((s) => (
            <tr key={s.shot_id} className="border-t border-line-soft font-mono text-cream-dim">
              <td className="py-1.5 text-cream">#{s.shot_id}</td>
              <td className="py-1.5">1:{s.brew_ratio.toFixed(1)}</td>
              <td className="py-1.5">{s.duration_s.toFixed(1)}s</td>
              <td className="py-1.5">{s.peak_pressure_bar.toFixed(1)} bar</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Shell>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" aria-hidden>
      <path d="M3 8.5l3 3 7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
