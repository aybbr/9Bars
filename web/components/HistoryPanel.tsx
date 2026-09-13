"use client";

import { useChatContext } from "@/lib/chat-context";
import { cn } from "@/lib/cn";

export function HistoryPanel() {
  const { sessions, activeId, openSession } = useChatContext();

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-line-soft px-4 py-3">
        <span className="text-xs font-medium uppercase tracking-[0.14em] text-cream-faint">History</span>
      </header>
      <div className="flex-1 overflow-y-auto p-2">
        {sessions.length === 0 ? (
          <p className="px-2 py-10 text-center text-sm text-cream-faint">No conversations yet.</p>
        ) : (
          <ul className="space-y-0.5">
            {sessions.map((session) => (
              <li key={session.id}>
                <button
                  onClick={() => openSession(session.id)}
                  className={cn(
                    "flex w-full flex-col gap-0.5 rounded-xl px-3 py-2 text-left transition-colors",
                    session.id === activeId ? "bg-ground-3" : "hover:bg-ground-2",
                  )}
                >
                  <span className="truncate text-sm text-cream">{session.title || "New chat"}</span>
                  <span className="font-mono text-[11px] text-cream-faint">{formatTime(session.updatedAt)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function formatTime(ts: number): string {
  const minutes = Math.floor((Date.now() - ts) / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(ts).toLocaleDateString();
}
