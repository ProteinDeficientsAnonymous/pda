import { EventForm } from './form/EventForm';

export default function EventCreateScreen() {
  return (
    <main className="bg-brand-50 min-h-full">
      <div className="mx-auto max-w-3xl px-4 py-6 md:py-10">
        <h1 className="mb-5 text-2xl font-medium tracking-tight text-neutral-900">new event 🌱</h1>
        <EventForm />
      </div>
    </main>
  );
}
