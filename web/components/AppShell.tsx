"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useChatContext } from "@/lib/chat-context";
import { cn } from "@/lib/cn";

const LINKS = [
  { href: "/", label: "Chat" },
  { href: "/history", label: "Shots" },
  { href: "/events", label: "Events" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { turns, reset } = useChatContext();
  const showNewChat = pathname === "/" && turns.length > 0;

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-40 border-b border-line-soft bg-ground/85 backdrop-blur-md">
        <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-baseline gap-1.5">
            <span className="font-display text-2xl leading-none text-cream">
              <span className="crema-text">9</span>Bars
            </span>
            <span className="hidden text-[11px] uppercase tracking-[0.2em] text-cream-faint sm:inline">dial-in</span>
          </Link>
          <div className="flex items-center gap-1 sm:gap-2">
            {LINKS.map((link) => (
              <NavLink key={link.href} href={link.href}>
                {link.label}
              </NavLink>
            ))}
            {showNewChat && (
              <button
                onClick={reset}
                className="ml-2 inline-flex items-center gap-1.5 rounded-full border border-line bg-ground-3 px-3 py-1.5 text-sm text-cream transition-colors hover:border-crema/40 hover:text-crema-soft"
              >
                <PlusIcon />
                New chat
              </button>
            )}
          </div>
        </nav>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const active = pathname === href;
  return (
    <Link
      href={href}
      className={cn(
        "rounded-full px-3 py-1.5 text-sm transition-colors",
        active ? "bg-ground-3 text-cream" : "text-cream-dim hover:text-cream",
      )}
    >
      {children}
    </Link>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <path d="M8 3v10M3 8h10" strokeLinecap="round" />
    </svg>
  );
}
