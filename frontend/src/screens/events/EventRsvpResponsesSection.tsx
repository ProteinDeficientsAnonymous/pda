import { QuestionType } from '@/api/questionTypes';
import type { Event, EventGuest, EventRsvpQuestion } from '@/models/event';
import { RsvpServerStatus } from '@/models/event';

import { isRsvpRespondentStatus } from './rsvpQuestions';

interface ResponseColumn {
  key: string;
  id: string;
  label: string;
  fieldType?: EventRsvpQuestion['fieldType'];
  options: string[];
}

interface Props {
  event: Event;
}

/** Live questions plus orphaned snapshot keys so edits/deletes keep history visible. */
function responseColumns(
  questions: readonly EventRsvpQuestion[],
  guests: readonly EventGuest[],
): ResponseColumn[] {
  const cols: ResponseColumn[] = questions.map((q) => ({
    key: `${q.id}:${q.label}`,
    id: q.id,
    label: q.label,
    fieldType: q.fieldType,
    options: q.options,
  }));
  const seen = new Set(cols.map((column) => column.key));
  for (const g of guests) {
    for (const [qid, snap] of Object.entries(g.questionnaireResponses)) {
      const key = `${qid}:${snap.label}`;
      if (seen.has(key)) continue;
      seen.add(key);
      cols.push({ key, id: qid, label: snap.label, options: [] });
    }
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
            <ChoiceTallyCard key={q.key} question={q} guests={respondents} />
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
                  <th key={q.key} className="px-3 py-2">
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
                  {columns.map((q) => (
                    <td key={q.key} className="text-foreground px-3 py-2 whitespace-pre-wrap">
                      {renderAnswerForColumn(g.questionnaireResponses[q.id], q)}
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
    const snap = g.questionnaireResponses[question.id];
    if (snap?.label !== question.label) continue;
    const values =
      question.fieldType === QuestionType.Checkbox
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

function renderAnswerForColumn(
  snap: { label: string; answer: string } | undefined,
  column: ResponseColumn,
): string {
  if (snap?.label !== column.label) return '—';
  return snap.answer.trim().replaceAll(',', ', ') || '—';
}
