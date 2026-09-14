export type EvidenceItem = {
  source: "web" | "user_history" | "inferred";
  url: string | null;
  text: string;
  confidence: number;
};

export type Coffee = {
  coffee_id: string;
  name: string;
  roaster: string | null;
  origin: string | null;
  process: string | null;
  roast_level: string | null;
  roast_date: string | null;
  tasting_notes: string[];
  sources: string[];
  evidence: EvidenceItem[];
};

export type ShotSummary = {
  shot_id: string;
  coffee_id: string | null;
  machine_ref: string;
  dose_in_g: number;
  dose_out_g: number;
  peak_pressure_bar: number;
  avg_temp_c: number;
  brew_ratio: number;
  duration_s: number;
};

export type Telemetry = {
  shot_id: string;
  coffee_id: string | null;
  dose_in_g: number;
  dose_out_g: number;
  pressure: [number, number][];
  flow: [number, number][];
  temperature: [number, number][];
  weight: [number, number][];
};

export type Span = {
  tool_name: string;
  input_summary: string;
  output_summary: string;
  duration_ms: number;
};

export type NextAction = {
  changed_variable: string;
  current_value: number | string;
  proposed_value: number | string;
  rationale: string;
  confidence: number;
};

export type TasteFeedback = {
  shot_id: string;
  acidity: number;
  sweetness: number;
  body: number;
  overall: number;
  bitterness: number;
  aroma: number;
  finish: number;
  note: string | null;
};

export type Analysis = {
  shot_id: string;
  channeling_strength: string;
  channeling_explanation: string;
  flow_deviation: number;
};

export type DraftInput = {
  name: string;
  dose_g: number;
  yield_g: number;
  temp_c: number;
  grind_desc: string;
  rationale: string;
};

export type History = {
  shots: ShotSummary[];
  next_actions: NextAction[];
};

export type Artifact =
  | { kind: "research_coffee"; output: Coffee }
  | { kind: "draft_profile"; output: { draft_id: string }; input: DraftInput }
  | { kind: "propose_next_action"; output: NextAction }
  | { kind: "analyze_shot"; output: Analysis }
  | { kind: "lookup_history"; output: History }
  | { kind: "rate_shot"; input: { shot_id: string | null; coffee_id: string | null } };

export type Block =
  | { type: "text"; text: string }
  | { type: "tool"; name: string; output?: string }
  | { type: "artifact"; artifact: Artifact }
  | { type: "image"; dataUrl: string };

export type ChatEvent =
  | { type: "start"; mode: "live" | "demo" }
  | { type: "text"; text: string }
  | { type: "tool_start"; name: string; input: string }
  | { type: "tool_result"; name: string; output: string }
  | { type: "artifact"; kind: string; input: Record<string, unknown>; output: Record<string, unknown> }
  | { type: "done"; mode: "live" | "demo"; message?: string }
  | { type: "error"; message: string };
