import { ChatPanel } from "@/components/ChatPanel";
import { HistoryPanel } from "@/components/HistoryPanel";

export default function ChatPage() {
  return (
    <div className="mx-auto flex h-[calc(100dvh-4rem)] max-w-7xl">
      <div className="min-w-0 flex-1">
        <ChatPanel />
      </div>
      <aside className="hidden w-[320px] shrink-0 border-l border-line-soft bg-ground/40 lg:block">
        <HistoryPanel />
      </aside>
    </div>
  );
}
