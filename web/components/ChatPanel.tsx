"use client";

import { useRef, useState, type ChangeEvent } from "react";
import { useChatContext } from "@/lib/chat-context";
import { fileToDataUrl } from "@/lib/image";
import type { ChatTurn } from "@/lib/useChat";
import { ArtifactBlock } from "./artifacts";
import { Markdown } from "./Markdown";
import { BrewingSpinner, CremaSwirl } from "./motifs";
import { Button } from "./ui";

const SUGGESTIONS = [
  { title: "Research a coffee", prompt: "Research this coffee: ", icon: <BeanIcon /> },
  { title: "Review my last shot", prompt: "How was my last shot?", icon: <GaugeIcon /> },
  { title: "One change", prompt: "Propose one change for the next pull", icon: <ArrowIcon /> },
];

export function ChatPanel() {
  const { turns, busy, send, reset } = useChatContext();
  const [input, setInput] = useState("");
  const [image, setImage] = useState<string | undefined>();
  const fileRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function runDemo() {
    reset();
    void send("Walk me through dialing in this coffee.");
  }

  function fillPrompt(prompt: string) {
    setInput(prompt);
    textareaRef.current?.focus();
  }

  async function onPickImage(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      setImage(await fileToDataUrl(file));
    } catch {
      /* ignore unreadable image */
    }
  }

  function submit() {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setImage(undefined);
    void send(text, image);
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-8 sm:px-6">
        {turns.length === 0 ? (
          <EmptyState onSuggestion={fillPrompt} onDemo={runDemo} />
        ) : (
          <div className="mx-auto flex max-w-2xl flex-col gap-7 pb-4">
            {turns.map((turn) => (
              <Turn key={turn.id} turn={turn} />
            ))}
            {busy && (
              <div className="flex items-center gap-2.5 text-sm text-cream-dim animate-fade">
                <BrewingSpinner />
                <span className="italic">Pulling…</span>
              </div>
            )}
          </div>
        )}
      </div>
      <Composer
        value={input}
        onChange={setInput}
        onSubmit={submit}
        busy={busy}
        image={image}
        onPickImage={() => fileRef.current?.click()}
        onClearImage={() => setImage(undefined)}
        textareaRef={textareaRef}
      />
      <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={onPickImage} />
    </div>
  );
}

function EmptyState({ onSuggestion, onDemo }: { onSuggestion: (s: string) => void; onDemo: () => void }) {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center pt-8 text-center">
      <CremaSwirl className="h-36 w-36 opacity-90" />
      <h1 className="mt-7 font-display text-4xl text-cream sm:text-5xl">
        Dial in your <span className="crema-text">next shot</span>.
      </h1>
      <p className="mt-4 max-w-md text-base leading-relaxed text-cream-dim">
        Nine bars of pressure, none on you. I research the coffee, draft a profile for your approval, and turn your
        taste into exactly one change at a time.
      </p>

      <div className="mt-8 grid w-full max-w-md grid-cols-1 gap-2.5 sm:grid-cols-3">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.title}
            onClick={() => onSuggestion(s.prompt)}
            className="group flex flex-col items-start gap-2 rounded-2xl border border-line-soft bg-ground-2/70 p-4 text-left transition-colors hover:border-crema/40 hover:bg-ground-3"
          >
            <span className="text-crema">{s.icon}</span>
            <span className="text-sm font-medium text-cream group-hover:text-crema-soft">{s.title}</span>
            <span className="line-clamp-2 text-xs text-cream-faint">{s.prompt}</span>
          </button>
        ))}
      </div>

      <button onClick={onDemo} className="mt-6 text-xs text-cream-faint underline decoration-line underline-offset-4 transition-colors hover:text-cream-dim">
        View a scripted demo
      </button>
    </div>
  );
}

function Turn({ turn }: { turn: ChatTurn }) {
  if (turn.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] animate-rise space-y-2">
          {turn.blocks.map((block, i) => {
            if (block.type === "image") {
              return (
                <img
                  key={i}
                  src={block.dataUrl}
                  alt="Coffee bag"
                  className="ml-auto w-40 rounded-xl border border-line object-cover"
                />
              );
            }
            return null;
          })}
          <div className="rounded-2xl rounded-br-sm bg-ground-3 px-4 py-2.5 text-sm leading-relaxed text-cream">
            {turn.blocks.find((b) => b.type === "text")?.text ?? ""}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-rise space-y-3">
      {turn.blocks.map((block, i) => {
        if (block.type === "text") return <Markdown key={i}>{block.text}</Markdown>;
        if (block.type === "tool") {
          return (
            <div key={i} className="flex items-center gap-2 text-xs text-cream-faint">
              <span className="h-1.5 w-1.5 rounded-full bg-copper" aria-hidden />
              <span className="font-mono">{block.name}</span>
              {block.output === undefined && <BrewingSpinner className="h-3 w-3" />}
            </div>
          );
        }
        if (block.type === "image") return null;
        return <ArtifactBlock key={i} artifact={block.artifact} />;
      })}
    </div>
  );
}

function Composer({
  value,
  onChange,
  onSubmit,
  busy,
  image,
  onPickImage,
  onClearImage,
  textareaRef,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  busy: boolean;
  image?: string;
  onPickImage: () => void;
  onClearImage: () => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
}) {
  return (
    <div className="hairline border-t border-line-soft bg-ground/80 px-4 py-3 backdrop-blur">
      <div className="mx-auto flex max-w-2xl items-end gap-3">
        <button
          type="button"
          onClick={onPickImage}
          aria-label="Attach a photo of your coffee bag"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-line bg-ground-2 text-cream-dim transition-colors hover:border-crema/40 hover:text-cream"
        >
          <CameraIcon />
        </button>
        <div className="flex min-w-0 flex-1 flex-col rounded-2xl border border-line bg-ground-2 focus-within:border-crema/50">
          {image && (
            <div className="flex items-center gap-2 border-b border-line-soft px-3 py-2">
              <img src={image} alt="Coffee bag" className="h-10 w-10 rounded-lg object-cover" />
              <span className="text-xs text-cream-dim">Photo attached</span>
              <button
                type="button"
                onClick={onClearImage}
                aria-label="Remove photo"
                className="ml-auto text-cream-faint transition-colors hover:text-rust"
              >
                ×
              </button>
            </div>
          )}
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSubmit();
              }
            }}
            rows={1}
            placeholder="Ask about a coffee, a shot, or the next change…"
            className="max-h-40 flex-1 resize-none bg-transparent px-4 py-3 text-sm text-cream placeholder:text-cream-faint focus:outline-none"
          />
        </div>
        <Button onClick={onSubmit} disabled={busy || (!value.trim() && !image)} className="shrink-0 px-4 py-2.5">
          {busy ? <BrewingSpinner /> : "Pull"}
        </Button>
      </div>
    </div>
  );
}

function BeanIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <ellipse cx="12" cy="12" rx="7" ry="10" />
      <path d="M12 2c0 6 2 12 0 20" strokeLinecap="round" />
    </svg>
  );
}

function GaugeIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <path d="M4 14a8 8 0 1 1 16 0" strokeLinecap="round" />
      <path d="M12 14l4-4" strokeLinecap="round" />
      <circle cx="12" cy="14" r="1.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <path d="M5 19l14-14" strokeLinecap="round" />
      <path d="M14 5h5v5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CameraIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <path d="M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1Z" strokeLinejoin="round" />
      <circle cx="12" cy="14" r="3.5" />
    </svg>
  );
}
