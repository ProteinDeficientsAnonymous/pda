import { newRsvpQuestionId } from '@/api/eventRsvpQuestions';
import { QuestionType } from '@/api/questionTypes';

import type { RsvpQuestionDraft } from '../rsvpQuestions';

const YES = 'Yes';

const OFFICIAL_QUESTIONS: readonly Omit<RsvpQuestionDraft, 'id'>[] = [
  {
    label: 'Do you understand that your RSVP is not confirmed until you pay?',
    fieldType: QuestionType.Select,
    options: [YES],
    required: true,
  },
  {
    label:
      'Do you understand that payments are not refundable for cancellations within 5 days of the event?',
    fieldType: QuestionType.Select,
    options: [YES],
    required: true,
  },
  {
    label:
      'Do you understand that your payment is for your share of the group order and will not be returned to you?',
    fieldType: QuestionType.Select,
    options: [YES],
    required: true,
  },
  {
    label:
      'We repost content on IG that is critical of ICE and supportive of Palestine. We share group and candid photos from events. Do you consent to being in photos on our IG (opt out is totally fine!)?',
    fieldType: QuestionType.Select,
    options: ['Yes, I consent to being on the IG', "No, I'd like to opt out"],
    required: true,
  },
];

function isUntouchedOfficial(q: RsvpQuestionDraft): boolean {
  return OFFICIAL_QUESTIONS.some(
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
): RsvpQuestionDraft[] {
  if (!official) {
    const kept = questions.filter((q) => !isUntouchedOfficial(q));
    return kept.length === questions.length ? questions : kept;
  }
  const labels = new Set(questions.map((q) => q.label));
  const missing = OFFICIAL_QUESTIONS.filter((o) => !labels.has(o.label));
  if (missing.length === 0) return questions;
  return [
    ...questions,
    ...missing.map((o) => ({ ...o, options: [...o.options], id: newRsvpQuestionId() })),
  ];
}
