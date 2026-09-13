import { EventLog } from "@/components/EventLog";

export default function EventsPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <h1 className="font-display text-3xl text-cream">Events</h1>
      <p className="mt-1 text-sm text-cream-dim">The domain events streamed from the bar.</p>
      <div className="mt-6">
        <EventLog />
      </div>
    </div>
  );
}
