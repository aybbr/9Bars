// Pure geometry + config for the interactive "Taste Bloom" rating radar.
//
// Everything here is a deterministic function of its inputs (no React, no DOM),
// so it can be unit-tested and shared across the Shots page and the chat
// artifact without drifting.

export type TasteKey = "acidity" | "sweetness" | "bitterness" | "body" | "aroma" | "finish";

export type TasteRating = {
  acidity: number;
  sweetness: number;
  bitterness: number;
  body: number;
  aroma: number;
  finish: number;
  overall: number;
};

export type TasteAxis = {
  key: TasteKey;
  label: string;
  low: string;
  high: string;
};

export const TASTE_AXES: readonly TasteAxis[] = [
  { key: "acidity", label: "Acidity", low: "flat", high: "bright" },
  { key: "sweetness", label: "Sweetness", low: "dry", high: "sweet" },
  { key: "bitterness", label: "Bitterness", low: "smooth", high: "bitter" },
  { key: "body", label: "Body", low: "thin", high: "syrupy" },
  { key: "aroma", label: "Aroma", low: "muted", high: "fragrant" },
  { key: "finish", label: "Finish", low: "short", high: "lingering" },
];

export const MIN_VALUE = 1;
export const MAX_VALUE = 5;
export const VALUE_STEP = 0.5;

// viewBox geometry (bean squash: slightly shorter vertically than horizontally)
export const VIEWBOX = 240;
export const CENTER = VIEWBOX / 2;
export const RADIUS_X = 88;
export const RADIUS_Y = 82;
export const INNER_RADIUS = 12;
export const LABEL_RADIUS = 104;

export type Point = { x: number; y: number };

export function defaultRating(): TasteRating {
  return { acidity: 3, sweetness: 3, bitterness: 3, body: 3, aroma: 3, finish: 3, overall: 3 };
}

function angleFor(index: number): number {
  return -Math.PI / 2 + index * ((2 * Math.PI) / TASTE_AXES.length);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function lerp(from: number, to: number, t: number): number {
  return from + (to - from) * t;
}

export function axisPoint(index: number, value: number): Point {
  const angle = angleFor(index);
  const t = (clamp(value, MIN_VALUE, MAX_VALUE) - MIN_VALUE) / (MAX_VALUE - MIN_VALUE);
  const rx = lerp(INNER_RADIUS, RADIUS_X, t);
  const ry = lerp(INNER_RADIUS, RADIUS_Y, t);
  return { x: CENTER + Math.cos(angle) * rx, y: CENTER + Math.sin(angle) * ry };
}

export function axisAngle(index: number): number {
  return angleFor(index);
}

export function labelPoint(index: number): Point {
  const angle = angleFor(index);
  return { x: CENTER + Math.cos(angle) * LABEL_RADIUS, y: CENTER + Math.sin(angle) * LABEL_RADIUS };
}

export function valuePoints(values: TasteRating): Point[] {
  return TASTE_AXES.map((axis, index) => axisPoint(index, values[axis.key]));
}

export function ringPoints(level: number): Point[] {
  return TASTE_AXES.map((_, index) => axisPoint(index, level));
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

// Closed Catmull-Rom → cubic bezier path through the points, giving the
// organic "bean" curve instead of a straight polygon.
export function smoothPath(points: readonly Point[]): string {
  if (points.length === 0) return "";
  if (points.length < 3) {
    return points.map((p, i) => `${i === 0 ? "M" : "L"}${round2(p.x)},${round2(p.y)}`).join(" ");
  }
  const n = points.length;
  const parts: string[] = [`M${round2(points[0].x)},${round2(points[0].y)}`];
  for (let i = 0; i < n; i++) {
    const p0 = points[(i - 1 + n) % n];
    const p1 = points[i];
    const p2 = points[(i + 1) % n];
    const p3 = points[(i + 2) % n];
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    parts.push(`C${round2(c1x)},${round2(c1y)} ${round2(c2x)},${round2(c2y)} ${round2(p2.x)},${round2(p2.y)}`);
  }
  return `${parts.join(" ")} Z`;
}

function nearestAxisIndex(angle: number): number {
  const step = (2 * Math.PI) / TASTE_AXES.length;
  let index = Math.round((angle + Math.PI / 2) / step) % TASTE_AXES.length;
  if (index < 0) index += TASTE_AXES.length;
  return index;
}

function snap(value: number): number {
  return clamp(Math.round(value / VALUE_STEP) * VALUE_STEP, MIN_VALUE, MAX_VALUE);
}

// Map a pointer position (SVG coordinates) to an axis index and snapped value.
export function valueFromPointer(x: number, y: number): { index: number; value: number } {
  const dx = x - CENTER;
  const dy = y - CENTER;
  const angle = Math.atan2(dy, dx);
  const index = nearestAxisIndex(angle);
  const axisAngle = angleFor(index);
  const projection = dx * Math.cos(axisAngle) + dy * Math.sin(axisAngle);
  const maxRadius = Math.hypot(RADIUS_X * Math.cos(axisAngle), RADIUS_Y * Math.sin(axisAngle));
  const t = (projection - INNER_RADIUS) / (maxRadius - INNER_RADIUS);
  return { index, value: snap(MIN_VALUE + t * (MAX_VALUE - MIN_VALUE)) };
}

export function descriptorFor(key: TasteKey, value: number): string {
  const axis = TASTE_AXES.find((a) => a.key === key);
  if (!axis) return "";
  return value <= (MIN_VALUE + MAX_VALUE) / 2 ? axis.low : axis.high;
}

export function describeRating(rating: TasteRating, shotId: string): string {
  const taste = TASTE_AXES.map((axis) => `${axis.label.toLowerCase()} ${rating[axis.key]}/5`).join(", ");
  return (
    `I just tasted shot #${shotId} and rated it — ${taste}, overall ${rating.overall}/5. ` +
    "Save this feedback and propose the single change for the next pull."
  );
}
