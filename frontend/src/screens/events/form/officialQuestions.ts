import { newRsvpQuestionId } from '@/api/eventRsvpQuestions';
import type { OfficialRsvpQuestion } from '@/api/officialEventDefaults';

import type { RsvpQuestionDraft } from '../rsvpQuestions';

function isUntouchedOfficial(q: RsvpQuestionDraft, official: readonly OfficialRsvpQuestion[]) {
  return official.some(
    (o) =>
      o.label === q.label &&
      o.fieldType === q.fieldType &&
      o.required === q.required &&
      o.options.join('\n') === q.options.join('\n'),
  );
}

// Adds missing official questions, or drops the unedited ones once the event stops being official.
export function withOfficialQuestions(
  questions: RsvpQuestionDraft[],
  official: boolean,
  officialQuestions: readonly OfficialRsvpQuestion[],
): RsvpQuestionDraft[] {
  if (!official) {
    const kept = questions.filter((q) => !isUntouchedOfficial(q, officialQuestions));
    return kept.length === questions.length ? questions : kept;
  }
  const labels = new Set(questions.map((q) => q.label));
  const missing = officialQuestions.filter((o) => !labels.has(o.label));
  if (missing.length === 0) return questions;
  return [
    ...questions,
    ...missing.map((o) => ({ ...o, options: [...o.options], id: newRsvpQuestionId() })),
  ];
}
