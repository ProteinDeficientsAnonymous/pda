import { useParams } from 'react-router-dom';
import { useEvent } from '@/api/events';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { EventForm } from './form/EventForm';

export default function EventEditScreen() {
  const { id } = useParams<{ id: string }>();
  const { data: event, isPending, isError } = useEvent(id);
  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load this event — try refreshing" />;
  return (
    <main className="bg-brand-50 min-h-full">
      <div className="mx-auto max-w-3xl px-4 py-6 md:py-10">
        <h1 className="mb-5 text-2xl font-medium tracking-tight text-neutral-900">edit event</h1>
        <EventForm existing={event} />
      </div>
    </main>
  );
}
