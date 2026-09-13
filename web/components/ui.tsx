import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "outline" }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-all",
        "disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-crema/60",
        variant === "primary" &&
          "bg-crema text-ground hover:bg-crema-soft active:scale-[0.98] shadow-[0_0_0_1px_rgba(232,160,76,0.2),0_6px_24px_-8px_rgba(232,160,76,0.5)]",
        variant === "ghost" && "text-cream-dim hover:bg-ground-3 hover:text-cream",
        variant === "outline" && "border border-line text-cream hover:border-crema/40 hover:bg-ground-3",
        className,
      )}
      {...props}
    />
  );
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-line-soft bg-ground-2/80 shadow-[0_20px_50px_-30px_rgba(0,0,0,0.8)] backdrop-blur-sm",
        className,
      )}
      {...props}
    />
  );
}

export function Badge({
  className,
  tone = "crema",
  children,
}: {
  className?: string;
  tone?: "crema" | "olive" | "rust" | "neutral";
  children: ReactNode;
}) {
  const tones = {
    crema: "border-crema/30 bg-crema/10 text-crema-soft",
    olive: "border-olive/30 bg-olive/10 text-olive",
    rust: "border-rust/30 bg-rust/10 text-rust",
    neutral: "border-line bg-ground-3 text-cream-dim",
  } as const;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function ToolChip({ name, input, output, running }: { name: string; input?: string; output?: string; running?: boolean }) {
  return (
    <div className="my-1 flex items-start gap-2.5 rounded-xl border border-line-soft bg-ground-3/60 px-3 py-2 text-xs">
      {running ? (
        <BrewingIcon />
      ) : (
        <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-copper" />
      )}
      <div className="min-w-0">
        <span className="font-mono text-cream">{name}</span>
        {output && <span className="ml-2 text-cream-dim">· {output}</span>}
      </div>
    </div>
  );
}

function BrewingIcon() {
  return (
    <span className="mt-0.5 h-3 w-3 shrink-0 animate-spin rounded-full border border-copper/40 border-t-copper" aria-hidden />
  );
}

export function MonoStat({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] uppercase tracking-wider text-cream-faint">{label}</span>
      <span className="font-mono text-sm text-cream">
        {value}
        {unit && <span className="ml-1 text-xs text-cream-faint">{unit}</span>}
      </span>
    </div>
  );
}
