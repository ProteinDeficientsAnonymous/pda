import { EventForm } from './form/EventForm';

export default function EventCreateScreen() {
  return (
    <main className="bg-background min-h-full">
      <div className="mx-auto max-w-6xl px-4 py-6 md:py-10">
        <EventForm />
      </div>
    </main>
  );
}
