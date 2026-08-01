import type { Event, EventGuest, EventRsvpQuestion } from '@/models/event';
import { RsvpServerStatus } from '@/models/event';

/** Guests who typically answered questions (going / maybe / waitlisted). */
const RESPONSE_STATUSES = new Set<string>([
  RsvpServerStatus.Attending,
  RsvpServerStatus.Maybe,
  RsvpServerStatus.Waitlisted,
]);

interface Props {
  event: Event;
  /** Hide the section heading when shown inside a titled dialog. */
  embedded?: boolean;
}

export function EventRsvpResponsesSection({ event, embedded = false }: Props) {
  const questions = event.rsvpQuestions;
  if (questions.length === 0) return null;

  const respondents = event.guests.filter((g) => RESPONSE_STATUSES.has(g.status));
  const choiceQuestions = questions.filter(
    (q) => q.fieldType === 'dropdown' || q.fieldType === 'multiselect',
  );

  return (
    <section aria-label="question responses" className="flex flex-col gap-4">
      <div>
        {embedded ? null : <h2 className="text-base font-medium">question responses</h2>}
        <p className="text-muted text-sm">
          {String(respondents.length)} guest{respondents.length === 1 ? '' : 's'} with going / maybe
          / waitlist
        </p>
      </div>

      {choiceQuestions.length > 0 ? (
        <div className="flex flex-col gap-3">
          <h3 className="text-muted text-xs font-medium tracking-wide">tallies</h3>
          {choiceQuestions.map((q) => (
            <ChoiceTallyCard key={q.id} question={q} guests={respondents} />
          ))}
        </div>
      ) : null}

      {respondents.length === 0 ? (
        <p className="text-muted text-sm">no responses yet</p>
      ) : (
        <div className="border-border bg-surface overflow-x-auto rounded-lg border">
          <table className="w-full text-left text-sm">
            <thead className="bg-background text-muted text-xs">
              <tr>
                <th className="px-3 py-2">guest</th>
                <th className="px-3 py-2">status</th>
                {questions.map((q) => (
                  <th key={q.id} className="px-3 py-2">
                    {q.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {respondents.map((g) => (
                <tr key={g.userId} className="border-border border-t align-top">
                  <td className="text-foreground px-3 py-2">{g.name}</td>
                  <td className="text-muted px-3 py-2 text-xs">{statusLabel(g.status)}</td>
                  {questions.map((q) => (
                    <td key={q.id} className="text-foreground px-3 py-2 whitespace-pre-wrap">
                      {renderAnswer(g.answers[q.id])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function ChoiceTallyCard({
  question,
  guests,
}: {
  question: EventRsvpQuestion;
  guests: EventGuest[];
}) {
  const counts = new Map<string, number>();
  for (const opt of question.options) counts.set(opt, 0);

  let answered = 0;
  for (const g of guests) {
    const snap = g.answers[question.id];
    if (!snap) continue;
    const values =
      question.fieldType === 'multiselect'
        ? snap.answer.split(',').filter(Boolean)
        : snap.answer
          ? [snap.answer]
          : [];
    if (values.length === 0) continue;
    answered += 1;
    for (const v of values) {
      counts.set(v, (counts.get(v) ?? 0) + 1);
    }
  }

  return (
    <div className="border-border bg-surface rounded-lg border p-3">
      <p className="text-foreground mb-1 text-sm font-medium">{question.label}</p>
      <p className="text-muted mb-2 text-xs">
        {String(answered)} answer{answered === 1 ? '' : 's'}
      </p>
      <ul className="flex flex-col gap-1 text-sm">
        {[...counts.entries()].map(([opt, n]) => (
          <li key={opt} className="flex justify-between gap-4">
            <span className="text-foreground">{opt}</span>
            <span className="text-muted tabular-nums">{String(n)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function statusLabel(status: string): string {
  if (status === RsvpServerStatus.Attending) return 'going';
  if (status === RsvpServerStatus.Maybe) return 'maybe';
  if (status === RsvpServerStatus.Waitlisted) return 'waitlist';
  return status;
}

function renderAnswer(snap: { label: string; answer: string } | undefined): string {
  if (!snap) return '—';
  return snap.answer.trim().replaceAll(',', ', ') || '—';
}
