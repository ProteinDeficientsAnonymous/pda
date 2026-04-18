import { useParams } from 'react-router-dom';
import { useEvent } from '@/api/events';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { EventForm } from './form/EventForm';

export default function EventEditScreen() {
  const { id } = useParams<{ id: string }>();
  const { data: event, isPending, isError } = useEvent(id);
  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load this event — try refreshing" />;
  return (
    <ContentContainer>
      <h1 className="mb-6 text-2xl font-medium tracking-tight">edit event</h1>
      <EventForm existing={event} />
    </ContentContainer>
  );
}
