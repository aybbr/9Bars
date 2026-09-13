"use client";

import { useCallback, useRef } from "react";
import {
  MAX_VALUE,
  MIN_VALUE,
  TASTE_AXES,
  VALUE_STEP,
  VIEWBOX,
  axisAngle,
  axisPoint,
  descriptorFor,
  labelPoint,
  ringPoints,
  smoothPath,
  valueFromPointer,
  valuePoints,
  type TasteRating,
  type TasteKey,
} from "@/lib/taste";

const RING_LEVELS = [1, 2, 3, 4, 5];

type Props = {
  value: TasteRating;
  onChange: (next: TasteRating) => void;
  disabled?: boolean;
};

export function TasteBloom({ value, onChange, disabled = false }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const dragging = useRef(false);

  const setAxis = useCallback(
    (key: TasteKey, next: number) => {
      onChange({ ...value, [key]: next });
    },
    [value, onChange],
  );

  const pointFromEvent = useCallback((event: React.PointerEvent) => {
    const svg = svgRef.current;
    if (!svg) return null;
    const rect = svg.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * VIEWBOX,
      y: ((event.clientY - rect.top) / rect.height) * VIEWBOX,
    };
  }, []);

  function handlePointerDown(event: React.PointerEvent) {
    if (disabled) return;
    dragging.current = true;
    event.currentTarget.setPointerCapture(event.pointerId);
    const point = pointFromEvent(event);
    if (point) {
      const { index, value: next } = valueFromPointer(point.x, point.y);
      setAxis(TASTE_AXES[index].key, next);
    }
  }

  function handlePointerMove(event: React.PointerEvent) {
    if (!dragging.current || disabled) return;
    const point = pointFromEvent(event);
    if (!point) return;
    const { index, value: next } = valueFromPointer(point.x, point.y);
    setAxis(TASTE_AXES[index].key, next);
  }

  function handlePointerUp() {
    dragging.current = false;
  }

  function nudge(key: TasteKey, delta: number) {
    if (disabled) return;
    const axis = TASTE_AXES.find((a) => a.key === key);
    if (!axis) return;
    const current = value[key];
    const next = Math.min(MAX_VALUE, Math.max(MIN_VALUE, current + delta));
    setAxis(key, Math.round(next / VALUE_STEP) * VALUE_STEP);
  }

  function onHandleKeyDown(key: TasteKey) {
    return (event: React.KeyboardEvent) => {
      switch (event.key) {
        case "ArrowUp":
        case "ArrowRight":
          event.preventDefault();
          nudge(key, VALUE_STEP);
          break;
        case "ArrowDown":
        case "ArrowLeft":
          event.preventDefault();
          nudge(key, -VALUE_STEP);
          break;
        case "Home":
          event.preventDefault();
          setAxis(key, MIN_VALUE);
          break;
        case "End":
          event.preventDefault();
          setAxis(key, MAX_VALUE);
          break;
      }
    };
  }

  const bloomPath = smoothPath(valuePoints(value));

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${VIEWBOX} ${VIEWBOX}`}
      role="group"
      aria-label="Taste bloom rating"
      className="h-full w-full touch-none select-none"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      <defs>
        <radialGradient id="taste-bloom-fill" cx="50%" cy="50%" r="50%">
          <stop offset="0%" style={{ stopColor: "var(--color-crema-soft)", stopOpacity: 0.85 }} />
          <stop offset="70%" style={{ stopColor: "var(--color-crema)", stopOpacity: 0.45 }} />
          <stop offset="100%" style={{ stopColor: "var(--color-copper)", stopOpacity: 0.18 }} />
        </radialGradient>
        <linearGradient id="taste-bloom-edge" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" style={{ stopColor: "var(--color-crema-soft)" }} />
          <stop offset="100%" style={{ stopColor: "var(--color-copper)" }} />
        </linearGradient>
      </defs>

      {RING_LEVELS.map((level) => (
        <path
          key={level}
          d={smoothPath(ringPoints(level))}
          fill="none"
          stroke="var(--color-line)"
          strokeWidth={level % 1 === 0 ? 1 : 0.75}
          opacity={0.55}
        />
      ))}

      {TASTE_AXES.map((axis, index) => {
        const outer = axisPoint(index, MAX_VALUE);
        return (
          <line
            key={axis.key}
            x1={VIEWBOX / 2}
            y1={VIEWBOX / 2}
            x2={outer.x}
            y2={outer.y}
            stroke="var(--color-line-soft)"
            strokeWidth={1}
            opacity={0.7}
          />
        );
      })}

      <path
        d={bloomPath}
        fill="url(#taste-bloom-fill)"
        stroke="url(#taste-bloom-edge)"
        strokeWidth={2}
        strokeLinejoin="round"
        style={{ filter: "drop-shadow(0 0 6px rgba(232,160,76,0.35))" }}
      />

      {TASTE_AXES.map((axis, index) => {
        const point = axisPoint(index, value[axis.key]);
        return (
          <g key={axis.key}>
            <circle cx={point.x} cy={point.y} r={9} fill="var(--color-crema)" opacity={0.18} />
            <circle
              cx={point.x}
              cy={point.y}
              r={4.5}
              fill="var(--color-crema)"
              stroke="var(--color-ground)"
              strokeWidth={1.5}
              tabIndex={disabled ? -1 : 0}
              role="slider"
              aria-label={axis.label}
              aria-valuemin={MIN_VALUE}
              aria-valuemax={MAX_VALUE}
              aria-valuenow={value[axis.key]}
              aria-valuetext={`${value[axis.key]} · ${descriptorFor(axis.key, value[axis.key])}`}
              onKeyDown={onHandleKeyDown(axis.key)}
              className="focus:outline-none focus:ring-2 focus:ring-crema/70"
              style={{ cursor: disabled ? "default" : "grab" }}
            />
          </g>
        );
      })}

      <g pointerEvents="none">
        {TASTE_AXES.map((axis, index) => {
          const label = labelPoint(index);
          const angle = axisAngle(index);
          const cos = Math.cos(angle);
          const anchor = cos > 0.5 ? "start" : cos < -0.5 ? "end" : "middle";
          return (
            <g key={axis.key}>
              <text
                x={label.x}
                y={label.y - 4}
                textAnchor={anchor}
                className="fill-cream-dim font-mono"
                style={{ fontSize: 9, letterSpacing: "0.08em" }}
              >
                {axis.label.toUpperCase()}
              </text>
              <text
                x={label.x}
                y={label.y + 8}
                textAnchor={anchor}
                className="fill-crema-soft font-mono"
                style={{ fontSize: 9 }}
              >
                {value[axis.key].toFixed(1)} · {descriptorFor(axis.key, value[axis.key])}
              </text>
            </g>
          );
        })}
        <text
          x={VIEWBOX / 2}
          y={VIEWBOX / 2 - 2}
          textAnchor="middle"
          className="fill-cream font-display"
          style={{ fontSize: 22 }}
        >
          {value.overall.toFixed(1)}
        </text>
        <text
          x={VIEWBOX / 2}
          y={VIEWBOX / 2 + 14}
          textAnchor="middle"
          className="fill-cream-faint font-mono"
          style={{ fontSize: 8, letterSpacing: "0.12em" }}
        >
          OVERALL
        </text>
      </g>
    </svg>
  );
}
