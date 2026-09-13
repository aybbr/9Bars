"use client";

import * as echarts from "echarts";
import { useEffect, useRef } from "react";
import { registerNineBarsTheme } from "@/lib/echarts";

registerNineBarsTheme();

export function EChart({ option, className }: { option: echarts.EChartsOption; className?: string }) {
  const host = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!host.current) return;
    const instance = echarts.init(host.current, "nine-bars");
    chart.current = instance;
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(host.current);
    return () => {
      observer.disconnect();
      instance.dispose();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    chart.current?.setOption(option, { notMerge: true });
  }, [option]);

  return <div ref={host} className={className} />;
}
