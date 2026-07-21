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
    <main className="bg-background min-h-full">
      <div className="mx-auto max-w-6xl px-4 py-6 md:py-10">
        <EventForm existing={event} />
      </div>
    </main>
  );
}
