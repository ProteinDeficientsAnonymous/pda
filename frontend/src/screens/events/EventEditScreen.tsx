import { useNavigate, useParams } from 'react-router-dom';
import { useEvent } from '@/api/events';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { EventForm } from './form/EventForm';

export default function EventEditScreen() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: event, isPending, isError } = useEvent(id);
  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load this event — try refreshing" />;
  return (
    <main className="bg-background min-h-full">
      <div className="mx-auto max-w-3xl px-4 py-6 md:py-10">
        <div className="mb-5 flex items-center justify-between">
          <h1 className="text-foreground text-2xl font-medium tracking-tight">edit event</h1>
          <button
            type="button"
            onClick={() => void navigate(-1)}
            className="text-muted hover:text-foreground-secondary text-sm"
          >
            cancel
          </button>
        </div>
        <EventForm existing={event} />
      </div>
    </main>
  );
}
