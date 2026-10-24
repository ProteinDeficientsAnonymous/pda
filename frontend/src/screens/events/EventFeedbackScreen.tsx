import { format, parseISO } from 'date-fns';
import { Link, useParams } from 'react-router-dom';

import { extractApiError, getApiStatus } from '@/api/apiErrors';
import { type HostEventFeedback, useHostEventFeedback } from '@/api/eventFeedbackHost';
import { useEvent } from '@/api/events';
import { renderAnswer } from '@/components/questions/renderAnswer';
import { eventPath } from '@/models/event';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function EventFeedbackScreen() {
  const { id } = useParams<{ id: string }>();
  const { data: event, isPending, isError } = useEvent(id);
  const feedback = useHostEventFeedback(id);

  if (isPending || feedback.isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load this event — try refreshing" />;
  if (feedback.isError) {
    if (getApiStatus(feedback.error) === 403) {
      const message =
        extractApiError(feedback.error) ?? 'only the host or a co-host can see event feedback';
      return <ContentError message={message} />;
    }
    return <ContentError message="couldn't load the feedback — try refreshing" />;
  }

  return (
    <ContentContainer>
      <Link
        to={eventPath(event)}
        className="text-foreground-secondary hover:text-foreground mb-4 inline-flex items-center gap-1 text-sm"
      >
        ← back to event
      </Link>
      <h1 className="mb-1 text-2xl font-medium tracking-tight">feedback</h1>
      <p className="text-foreground-secondary mb-6 text-sm">{event.title} — shared anonymously</p>
      <FeedbackBody feedback={feedback.data} />
    </ContentContainer>
  );
}

function FeedbackBody({ feedback }: { feedback: HostEventFeedback }) {
  if (feedback.responses.length === 0) {
    return <p className="text-muted text-sm">no feedback yet 🌿</p>;
  }
  return (
    <div className="flex flex-col gap-6">
      {feedback.questions.map((q) => {
        const entries = feedback.responses.filter((r) => r.answers[q.id] !== undefined);
        return (
          <section key={q.id} className="border-border bg-surface rounded-lg border p-4">
            <h2 className="mb-3 text-sm font-medium">{q.label.toLowerCase()}</h2>
            {entries.length === 0 ? (
              <p className="text-muted text-xs">no answers</p>
            ) : (
              <ul className="flex flex-col gap-3">
                {entries.map((r) => (
                  <li key={r.id} className="text-sm">
                    <p className="[overflow-wrap:anywhere] whitespace-pre-wrap">
                      {renderAnswer(r.answers[q.id])}
                    </p>
                    <p className="text-muted mt-0.5 text-xs">
                      {format(parseISO(r.submitted_on), 'MMM d, yyyy').toLowerCase()}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}
