import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { extractApiErrorOr, getApiStatus } from '@/api/apiErrors';
import { type EventSpeech, useEventSpeech, useSaveEventSpeech } from '@/api/eventSpeech';
import { HtmlContent } from '@/components/HtmlContent';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { EventSpeechForm } from './EventSpeechForm';

const READING_CLASS = [
  'text-lg [overflow-wrap:anywhere]',
  '[&_blockquote]:my-3 [&_blockquote]:border-yellow-400 [&_blockquote]:text-sm [&_blockquote]:italic',
].join(' ');

export default function EventSpeechScreen() {
  const { id } = useParams<{ id: string }>();
  const { data: speech, isPending, isError, error } = useEventSpeech(id);

  if (isPending) return <ContentLoading />;
  if (isError) {
    const status = getApiStatus(error);
    if (status === 403)
      return <ContentError message="only this event's hosts can see its speech" />;
    if (status === 404) return <ContentError message="speeches are only for official events" />;
    return <ContentError message="couldn't load this speech — try refreshing" />;
  }

  return <SpeechBody eventId={id ?? ''} speech={speech} />;
}

function SpeechBody({ eventId, speech }: { eventId: string; speech: EventSpeech }) {
  const readable = speech.saved && speech.officialKind !== null;
  const [editing, setEditing] = useState(!readable);
  const save = useSaveEventSpeech(eventId);
  const reading = !editing && readable;

  return (
    <ContentContainer>
      <Link
        to={`/events/${eventId}`}
        className="text-foreground-secondary hover:text-foreground mb-4 inline-flex items-center gap-1 text-sm"
      >
        ← back to event
      </Link>
      <div className="mb-1 flex items-center justify-between gap-2">
        <h1 className="text-2xl font-medium tracking-tight">event speech</h1>
      </div>
      <p className="text-foreground-secondary text-lg">{speech.eventTitle}</p>
      <div className="mb-6" />
      {reading ? (
        <HtmlContent html={speech.html} className={READING_CLASS} />
      ) : (
        <EventSpeechForm
          speech={speech}
          saving={save.isPending}
          error={save.isError ? extractApiErrorOr(save.error, "couldn't save — try again") : null}
          onSave={(input) => {
            save.mutate(input, {
              onSuccess: () => {
                setEditing(false);
                window.scrollTo(0, 0);
              },
            });
          }}
        />
      )}
    </ContentContainer>
  );
}
