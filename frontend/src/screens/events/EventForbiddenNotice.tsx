import { Link } from 'react-router-dom';

import { ContentContainer } from '@/screens/public/ContentContainer';

export function EventForbiddenNotice({
  eventId,
  message,
}: {
  eventId: string | undefined;
  message: string;
}) {
  return (
    <ContentContainer>
      <section className="border-border bg-surface mt-8 rounded-lg border p-6">
        <h2 className="mb-2 text-base font-medium">{message}</h2>
        <Link
          to={eventId ? `/events/${eventId}` : '/calendar'}
          className="border-border-strong text-foreground-secondary hover:bg-background mt-4 inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium"
        >
          back to event
        </Link>
      </section>
    </ContentContainer>
  );
}
