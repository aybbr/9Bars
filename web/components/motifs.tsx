import { cn } from "@/lib/cn";

const TONES = {
  crema: "var(--color-crema)",
  olive: "var(--color-olive)",
  rust: "var(--color-rust)",
  copper: "var(--color-copper)",
} as const;

export function BrewDot({ tone = "crema", className }: { tone?: keyof typeof TONES; className?: string }) {
  const color = TONES[tone];
  return (
    <span className={cn("relative inline-flex h-2.5 w-2.5", className)} aria-hidden>
      <span
        className="absolute inline-flex h-full w-full animate-brew-pulse rounded-full opacity-50"
        style={{ backgroundColor: color }}
      />
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
    </span>
  );
}

export function CremaSwirl({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 240 240" className={className} fill="none" aria-hidden>
      <defs>
        <radialGradient id="cremaGrad" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#f5cd8e" />
          <stop offset="55%" stopColor="#e8a04c" />
          <stop offset="100%" stopColor="#b07a45" stopOpacity="0" />
        </radialGradient>
      </defs>
      <g className="animate-swirl" style={{ transformOrigin: "120px 120px" }}>
        {[34, 62, 90, 118].map((r, i) => (
          <circle
            key={r}
            cx="120"
            cy="120"
            r={r}
            stroke="url(#cremaGrad)"
            strokeWidth={1.4 - i * 0.2}
            strokeDasharray={`${6 - i} ${8 + i}`}
            opacity={0.55 - i * 0.1}
          />
        ))}
      </g>
      <circle cx="120" cy="120" r="16" fill="url(#cremaGrad)" opacity="0.85" />
    </svg>
  );
}

export function Steam({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden>
      {[0, 1, 2].map((i) => (
        <path
          key={i}
          d={`M${4 + i * 8} 19c0-3 2-3 2-6`}
          stroke="var(--color-cream-faint)"
          strokeWidth="1.4"
          strokeLinecap="round"
          className="animate-steam"
          style={{ animationDelay: `${i * 0.7}s`, opacity: 0.5 }}
        />
      ))}
    </svg>
  );
}

export function BrewingSpinner({ className }: { className?: string }) {
  return (
    <span className={cn("relative inline-flex h-4 w-4", className)} aria-hidden>
      <span className="absolute inset-0 animate-spin rounded-full border border-crema/30 border-t-crema" />
    </span>
  );
}
