import { EventForm } from './form/EventForm';

export default function EventCreateScreen() {
  return (
    <main className="bg-background min-h-full">
      <div className="mx-auto max-w-6xl px-4 py-8">
        <EventForm />
      </div>
    </main>
  );
}
