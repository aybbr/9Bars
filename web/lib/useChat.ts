"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  Analysis,
  Artifact,
  Block,
  ChatEvent,
  Coffee,
  DraftInput,
  History,
  NextAction,
} from "./types";

const STORAGE_KEY = "nine-bars.chat.v2";

export type ChatTurn = {
  id: string;
  role: "user" | "assistant";
  blocks: Block[];
};

export type ChatSession = {
  id: string;
  title: string;
  updatedAt: number;
  turns: ChatTurn[];
};

type ChatState = { activeId: string; sessions: ChatSession[] };

function newId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function blankSession(): ChatSession {
  return { id: newId(), title: "", updatedAt: Date.now(), turns: [] };
}

function titleFrom(prompt: string): string {
  const text = prompt.trim();
  if (!text) return "New chat";
  return text.length > 48 ? `${text.slice(0, 47)}…` : text;
}

function loadState(): ChatState {
  if (typeof window === "undefined") {
    const session = blankSession();
    return { activeId: session.id, sessions: [session] };
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as ChatState;
      if (parsed && Array.isArray(parsed.sessions) && parsed.sessions.length > 0) {
        const sessions = parsed.sessions.filter((s) => s.turns.length > 0 || s.id === parsed.activeId);
        return { activeId: parsed.activeId, sessions };
      }
    }
  } catch {
    /* corrupted storage */
  }
  const session = blankSession();
  return { activeId: session.id, sessions: [session] };
}

function toArtifact(kind: string, input: Record<string, unknown>, output: Record<string, unknown>): Artifact | null {
  switch (kind) {
    case "research_coffee":
      return { kind, output: output as unknown as Coffee };
    case "draft_profile":
      return { kind, output: output as unknown as { draft_id: string }, input: input as unknown as DraftInput };
    case "propose_next_action":
      return { kind, output: output as unknown as NextAction };
    case "analyze_shot":
      return { kind, output: output as unknown as Analysis };
    case "lookup_history":
      return { kind, output: output as unknown as History };
    case "rate_shot":
      return { kind, input: input as unknown as { shot_id: string | null; coffee_id: string | null } };
    default:
      return null;
  }
}

export function useChat() {
  const [state, setState] = useState<ChatState>(loadState);
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const activeId = state.activeId;
  const activeSession = state.sessions.find((s) => s.id === activeId) ?? state.sessions[0];
  const turns = activeSession?.turns ?? [];
  const sessions = state.sessions
    .filter((s) => s.turns.length > 0)
    .sort((a, b) => b.updatedAt - a.updatedAt);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      /* storage unavailable */
    }
  }, [state]);

  const setTurns = useCallback((fn: (turns: ChatTurn[]) => ChatTurn[]) => {
    setState((s) => ({
      ...s,
      sessions: s.sessions.map((session) =>
        session.id === s.activeId ? { ...session, turns: fn(session.turns), updatedAt: Date.now() } : session,
      ),
    }));
  }, []);

  const send = useCallback(
    async (prompt: string, image?: string, demo = false) => {
      const userBlocks: Block[] = image
        ? [{ type: "image", dataUrl: image }, { type: "text", text: prompt }]
        : [{ type: "text", text: prompt }];
      const user: ChatTurn = { id: crypto.randomUUID(), role: "user", blocks: userBlocks };
      const assistant: ChatTurn = { id: crypto.randomUUID(), role: "assistant", blocks: [] };

      setState((s) => ({
        ...s,
        sessions: s.sessions.map((session) =>
          session.id === s.activeId
            ? {
                ...session,
                title: session.title || titleFrom(prompt),
                updatedAt: Date.now(),
                turns: [...session.turns, user, assistant],
              }
            : session,
        ),
      }));
      setBusy(true);

      const controller = new AbortController();
      abortRef.current = controller;
      const update = (fn: (blocks: Block[]) => Block[]) =>
        setTurns((turns) => turns.map((x) => (x.id === assistant.id ? { ...x, blocks: fn(x.blocks) } : x)));

      try {
        const res = await fetch("/api/agent/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt, image: image ?? undefined, session_id: activeId, demo }),
          signal: controller.signal,
        });
        if (!res.ok || !res.body) throw new Error("no stream");
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let idx;
          while ((idx = buffer.indexOf("\n\n")) !== -1) {
            const chunk = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            for (const line of chunk.split("\n")) {
              if (!line.startsWith("data: ")) continue;
              handle(JSON.parse(line.slice(6)) as ChatEvent);
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          update((blocks) => appendText(blocks, "Something went wrong while brewing."));
        }
      } finally {
        setBusy(false);
      }

      function handle(event: ChatEvent) {
        switch (event.type) {
          case "text":
            update((blocks) => appendText(blocks, event.text));
            break;
          case "tool_start":
            update((blocks) => [...blocks, { type: "tool", name: event.name }]);
            break;
          case "tool_result":
            update((blocks) => {
              const next = [...blocks];
              for (let i = next.length - 1; i >= 0; i--) {
                const block = next[i];
                if (block.type === "tool" && block.name === event.name && block.output === undefined) {
                  next[i] = { type: "tool", name: event.name, output: event.output };
                  return next;
                }
              }
              return [...next, { type: "tool", name: event.name, output: event.output }];
            });
            break;
          case "artifact": {
            const artifact = toArtifact(event.kind, event.input, event.output);
            if (artifact) update((blocks) => [...blocks, { type: "artifact", artifact }]);
            break;
          }
          case "done":
            if (event.message) {
              const message = event.message;
              update((blocks) => [...blocks.filter((b) => b.type !== "text"), { type: "text", text: message }]);
            }
            break;
          case "error":
            update((blocks) => appendText(blocks, event.message));
            break;
        }
      }
    },
    [activeId, setTurns],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const reset = useCallback(() => {
    setState((s) => {
      const blank = blankSession();
      return { activeId: blank.id, sessions: [...s.sessions.filter((session) => session.turns.length > 0), blank] };
    });
  }, []);

  const openSession = useCallback((id: string) => {
    setState((s) => (s.sessions.some((session) => session.id === id) ? { ...s, activeId: id } : s));
  }, []);

  return { turns, sessions, activeId, busy, send, stop, reset, openSession };
}

function appendText(blocks: Block[], text: string): Block[] {
  const last = blocks[blocks.length - 1];
  if (last && last.type === "text") {
    return [...blocks.slice(0, -1), { type: "text", text: last.text + text }];
  }
  return [...blocks, { type: "text", text }];
}
