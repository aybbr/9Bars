"use client";

import * as echarts from "echarts";
import { useMemo } from "react";
import { EChart } from "./EChart";
import type { Telemetry } from "@/lib/types";

export function ComparisonReport({ first, second }: { first: Telemetry; second: Telemetry }) {
  const option = useMemo<echarts.EChartsOption>(() => {
    const a = `#${first.shot_id}`;
    const b = `#${second.shot_id}`;
    return {
      animationDuration: 800,
      grid: { left: 40, right: 40, top: 30, bottom: 26 },
      tooltip: { trigger: "axis" },
      legend: {
        top: 0,
        textStyle: { color: "#bcae95", fontFamily: "var(--font-mono)", fontSize: 11 },
        data: [`${a} pressure`, `${b} pressure`, `${a} flow`, `${b} flow`],
      },
      xAxis: { type: "value", name: "s", min: 0 },
      yAxis: [
        { type: "value", name: "bar", max: 12, min: 0 },
        { type: "value", name: "g/s", min: 0, splitLine: { show: false } },
      ],
      series: [
        {
          name: `${a} pressure`,
          type: "line",
          data: first.pressure,
          symbol: "none",
          lineStyle: { color: "#8a7c67", width: 1.6, type: "dashed" },
        },
        {
          name: `${b} pressure`,
          type: "line",
          data: second.pressure,
          symbol: "none",
          lineStyle: { color: "#e8a04c", width: 2.2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(232,160,76,0.35)" },
              { offset: 1, color: "rgba(232,160,76,0)" },
            ]),
          },
        },
        {
          name: `${a} flow`,
          type: "line",
          yAxisIndex: 1,
          data: first.flow,
          symbol: "none",
          lineStyle: { color: "rgba(244,234,216,0.35)", width: 1.4 },
        },
        {
          name: `${b} flow`,
          type: "line",
          yAxisIndex: 1,
          data: second.flow,
          symbol: "none",
          lineStyle: { color: "#f4ead8", width: 1.8 },
        },
      ],
    };
  }, [first, second]);

  return (
    <div className="h-[300px]">
      <EChart option={option} className="h-full w-full" />
    </div>
  );
}
