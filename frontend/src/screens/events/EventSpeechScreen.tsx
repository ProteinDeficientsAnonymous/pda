import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { extractApiErrorOr, hasErrorCode } from '@/api/apiErrors';
import { type EventSpeech, useEventSpeech, useSaveEventSpeech } from '@/api/eventSpeech';
import { Code } from '@/api/validationCodes';
import { HtmlContent } from '@/components/HtmlContent';
import { Button } from '@/components/ui/Button';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { EventForbiddenNotice } from './EventForbiddenNotice';
import { EventSpeechForm } from './EventSpeechForm';

const READING_CLASS = [
  'text-lg [overflow-wrap:anywhere]',
  '[&_blockquote]:my-3 [&_blockquote]:border-yellow-400 [&_blockquote]:text-sm [&_blockquote]:italic',
].join(' ');

const ZOOM_STEPS = [1, 1.25, 1.5, 1.75, 2];
const ZOOM_STORAGE_KEY = 'pda-speech-zoom';

const LOAD_ERROR = "couldn't load this speech — try refreshing";
const NOTICE_CODES = [Code.Speech.HostsOnly, Code.Speech.OfficialEventRequired];

export default function EventSpeechScreen() {
  const { id } = useParams<{ id: string }>();
  const { data: speech, isPending, isError, error } = useEventSpeech(id);

  if (isPending) return <ContentLoading />;
  if (isError) {
    if (NOTICE_CODES.some((code) => hasErrorCode(error, code))) {
      return <EventForbiddenNotice eventId={id} message={extractApiErrorOr(error, LOAD_ERROR)} />;
    }
    return <ContentError message={LOAD_ERROR} />;
  }

  return <SpeechBody eventId={id ?? ''} speech={speech} />;
}

function storedZoomIndex(): number {
  const index = ZOOM_STEPS.indexOf(Number(localStorage.getItem(ZOOM_STORAGE_KEY)));
  return index === -1 ? 0 : index;
}

function useSpeechZoom() {
  const [index, setIndex] = useState(storedZoomIndex);
  const step = (delta: number) => {
    const next = Math.min(Math.max(index + delta, 0), ZOOM_STEPS.length - 1);
    localStorage.setItem(ZOOM_STORAGE_KEY, String(ZOOM_STEPS[next]));
    setIndex(next);
  };
  return {
    zoom: ZOOM_STEPS[index] ?? 1,
    canZoomOut: index > 0,
    canZoomIn: index < ZOOM_STEPS.length - 1,
    zoomOut: () => {
      step(-1);
    },
    zoomIn: () => {
      step(1);
    },
  };
}

function SpeechBody({ eventId, speech }: { eventId: string; speech: EventSpeech }) {
  const readable = speech.saved && speech.eventFormat !== null;
  const [editing, setEditing] = useState(!readable);
  const save = useSaveEventSpeech(eventId);
  const reading = !editing && readable;
  const { zoom, canZoomOut, canZoomIn, zoomOut, zoomIn } = useSpeechZoom();

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
        {reading ? (
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              aria-label="zoom out"
              disabled={!canZoomOut}
              onClick={zoomOut}
            >
              −
            </Button>
            <Button variant="secondary" aria-label="zoom in" disabled={!canZoomIn} onClick={zoomIn}>
              +
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                save.reset();
                setEditing(true);
              }}
            >
              edit
            </Button>
          </div>
        ) : null}
      </div>
      <p className="text-foreground-secondary text-lg">{speech.eventTitle}</p>
      {speech.saved && speech.updatedByName ? (
        <p className="text-muted mb-6 text-sm">updated by {speech.updatedByName.toLowerCase()}</p>
      ) : (
        <div className="mb-6" />
      )}
      {reading ? (
        <div style={{ zoom }}>
          <HtmlContent html={speech.html} className={READING_CLASS} />
        </div>
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
          onCancel={
            readable
              ? () => {
                  setEditing(false);
                }
              : undefined
          }
        />
      )}
    </ContentContainer>
  );
}
