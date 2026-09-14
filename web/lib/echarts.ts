import * as echarts from "echarts";

let registered = false;

export function registerNineBarsTheme() {
  if (registered) return;
  echarts.registerTheme("nine-bars", {
    color: ["#e8a04c", "#f4ead8", "#96a570", "#b07a45", "#c85e44"],
    backgroundColor: "transparent",
    textStyle: { color: "#bcae95", fontFamily: "var(--font-mono)" },
    line: { smooth: true, symbol: "none" },
    categoryAxis: {
      axisLine: { lineStyle: { color: "#3a2b1c" } },
      axisTick: { show: false },
      axisLabel: { color: "#8a7c67", fontFamily: "var(--font-mono)", fontSize: 10 },
      splitLine: { show: false },
    },
    valueAxis: {
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: "#8a7c67", fontFamily: "var(--font-mono)", fontSize: 10 },
      splitLine: { lineStyle: { color: "rgba(58,43,28,0.5)", type: "dashed" } },
    },
    tooltip: {
      backgroundColor: "#1b1510",
      borderColor: "#3a2b1c",
      textStyle: { color: "#f4ead8", fontFamily: "var(--font-mono)", fontSize: 11 },
      axisPointer: { lineStyle: { color: "rgba(232,160,76,0.4)" } },
    },
  });
  registered = true;
}
