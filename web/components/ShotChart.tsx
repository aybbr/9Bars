"use client";

import * as echarts from "echarts";
import { useMemo } from "react";
import { EChart } from "./EChart";
import type { Telemetry } from "@/lib/types";

const BAR_MAX = 12;
const NINE_BAR = 9;

export function ShotChart({ telemetry, height = 230 }: { telemetry: Telemetry; height?: number }) {
  const option = useMemo<echarts.EChartsOption>(
    () => ({
      animationDuration: 700,
      grid: { left: 44, right: 44, top: 18, bottom: 26 },
      tooltip: { trigger: "axis" },
      xAxis: {
        type: "value",
        name: "s",
        min: 0,
        splitLine: { show: false },
      },
      yAxis: [
        { type: "value", name: "bar", max: BAR_MAX, min: 0 },
        { type: "value", name: "g/s", min: 0, splitLine: { show: false } },
        { type: "value", name: "g", min: 0, splitLine: { show: false } },
      ],
      series: [
        {
          name: "pressure",
          type: "line",
          data: telemetry.pressure,
          symbol: "none",
          lineStyle: { color: "#e8a04c", width: 2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(232,160,76,0.4)" },
              { offset: 1, color: "rgba(232,160,76,0)" },
            ]),
          },
          markLine: {
            silent: true,
            symbol: "none",
            data: [{ yAxis: NINE_BAR }],
            lineStyle: { color: "rgba(244,234,216,0.3)", type: "dashed" },
            label: { formatter: "9 bar", color: "#bcae95", fontSize: 10 },
          },
        },
        {
          name: "flow",
          type: "line",
          yAxisIndex: 1,
          data: telemetry.flow,
          symbol: "none",
          lineStyle: { color: "#f4ead8", width: 1.5, opacity: 0.8 },
        },
        {
          name: "weight",
          type: "line",
          yAxisIndex: 2,
          data: telemetry.weight,
          symbol: "none",
          lineStyle: { color: "#96a570", width: 1.5, type: "dashed" },
        },
      ],
    }),
    [telemetry],
  );

  return (
    <div style={{ height }}>
      <EChart option={option} className="h-full w-full" />
    </div>
  );
}

export function PressureGauge({ value }: { value: number }) {
  const option = useMemo<echarts.EChartsOption>(
    () => ({
      series: [
        {
          type: "gauge",
          min: 0,
          max: BAR_MAX,
          startAngle: 210,
          endAngle: -30,
          radius: "100%",
          center: ["50%", "62%"],
          progress: { show: true, width: 7, itemStyle: { color: "#e8a04c" } },
          axisLine: { lineStyle: { width: 7, color: [[1, "#2a2017"]] } },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          pointer: { show: false },
          title: { show: true, offsetCenter: [0, "42%"], color: "#8a7c67", fontSize: 10 },
          detail: {
            valueAnimation: true,
            offsetCenter: [0, "-8%"],
            color: "#f4ead8",
            fontFamily: "var(--font-mono)",
            fontSize: 22,
            formatter: (v: number) => v.toFixed(1),
          },
          data: [{ value, name: "bar" }],
        },
      ],
    }),
    [value],
  );

  return (
    <div className="h-24 w-24">
      <EChart option={option} className="h-full w-full" />
    </div>
  );
}
