import { QuestionType } from '@/api/questionTypes';
import type { Event, EventGuest, EventRsvpQuestion } from '@/models/event';
import { rsvpGroupLabel } from '@/models/event';

import { isRsvpRespondentStatus } from './rsvpQuestions';

interface ResponseColumn {
  id: string;
  label: string;
  fieldType?: EventRsvpQuestion['fieldType'];
  options: string[];
}

interface Props {
  event: Event;
}

/** Live questions, plus deleted-question ids that still have saved guest answers. */
function responseColumns(
  questions: readonly EventRsvpQuestion[],
  guests: readonly EventGuest[],
): ResponseColumn[] {
  const cols: ResponseColumn[] = questions.map((q) => ({
    id: q.id,
    label: q.label,
    fieldType: q.fieldType,
    options: q.options,
  }));
  const liveIds = new Set(cols.map((column) => column.id));
  const orphanLabels = new Map<string, string>();
  for (const g of guests) {
    for (const [qid, snap] of Object.entries(g.questionnaireResponses)) {
      if (liveIds.has(qid) || orphanLabels.has(qid)) continue;
      orphanLabels.set(qid, snap.label);
    }
  }
  for (const [qid, label] of orphanLabels) {
    cols.push({ id: qid, label, options: [] });
  }
  return cols;
}

export function EventRsvpResponsesSection({ event }: Props) {
  const respondents = event.guests.filter((guest) => isRsvpRespondentStatus(guest.status));
  const columns = responseColumns(event.rsvpQuestions, respondents);
  if (columns.length === 0) return null;

  const choiceColumns = columns.filter(
    (q) => q.fieldType === QuestionType.Select || q.fieldType === QuestionType.Checkbox,
  );

  return (
    <section aria-label="question responses" className="flex flex-col gap-4">
      <div>
        <h2 className="text-base font-medium">question responses</h2>
        <p className="text-muted text-sm">
          {String(respondents.length)} guest{respondents.length === 1 ? '' : 's'} with going / maybe
          / waitlist
        </p>
      </div>

      {choiceColumns.length > 0 ? (
        <div className="flex flex-col gap-3">
          <h3 className="text-muted text-xs font-medium tracking-wide">tallies</h3>
          {choiceColumns.map((q) => (
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
                {columns.map((q) => (
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
                  <td className="text-muted px-3 py-2 text-xs">{rsvpGroupLabel(g.status)}</td>
                  {columns.map((q) => (
                    <td key={q.id} className="text-foreground px-3 py-2 whitespace-pre-wrap">
                      {renderAnswer(g.questionnaireResponses[q.id]?.answer)}
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

function ChoiceTallyCard({ question, guests }: { question: ResponseColumn; guests: EventGuest[] }) {
  const counts = new Map<string, number>();
  for (const opt of question.options) counts.set(opt, 0);

  let answered = 0;
  for (const g of guests) {
    const answer = g.questionnaireResponses[question.id]?.answer;
    if (!answer?.trim()) continue;
    const values =
      question.fieldType === QuestionType.Checkbox ? answer.split(',').filter(Boolean) : [answer];
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

function renderAnswer(answer: string | undefined): string {
  const trimmed = answer?.trim();
  if (!trimmed) return '—';
  return trimmed.replaceAll(',', ', ');
}
