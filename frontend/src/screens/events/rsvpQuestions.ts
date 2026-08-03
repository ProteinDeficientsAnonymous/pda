/** Draft / wire-aligned RSVP question helpers used by authoring + RSVP dialog. */

import type { RsvpQuestionType } from '@/api/eventRsvpQuestions';
import {
  QUESTION_TYPE_OPTION_BY_TYPE,
  questionTypeWantsOptions,
  type QuestionTypeOption,
} from '@/components/questions/questionTypeOptions';
import type { EventRsvpQuestion } from '@/models/event';

export type { RsvpQuestionType };
export type RsvpQuestionDraft = EventRsvpQuestion;
export type RsvpAnswerValue = string;

const RSVP_QUESTION_TYPE_OPTION_BY_TYPE = {
  textarea: QUESTION_TYPE_OPTION_BY_TYPE.textarea,
  dropdown: QUESTION_TYPE_OPTION_BY_TYPE.dropdown,
  multiselect: QUESTION_TYPE_OPTION_BY_TYPE.multiselect,
} satisfies Record<RsvpQuestionType, QuestionTypeOption>;

export const RSVP_QUESTION_TYPE_OPTIONS = Object.values(RSVP_QUESTION_TYPE_OPTION_BY_TYPE);

export const RSVP_QUESTION_TYPE_LABELS: Record<RsvpQuestionType, string> = Object.fromEntries(
  RSVP_QUESTION_TYPE_OPTIONS.map((o) => [o.value, o.label]),
) as Record<RsvpQuestionType, string>;

export function parseOptionsText(text: string): string[] {
  return text
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
}

export function isAnswerFilled(value: RsvpAnswerValue | undefined): boolean {
  return Boolean(value?.trim());
}

export function missingRequiredQuestionIds(
  questions: readonly RsvpQuestionDraft[],
  answers: Readonly<Record<string, RsvpAnswerValue | undefined>>,
): string[] {
  return questions.filter((q) => q.required && !isAnswerFilled(answers[q.id])).map((q) => q.id);
}

export function newQuestionId(): string {
  return `q-${crypto.randomUUID()}`;
}

export { questionTypeWantsOptions as wantsOptions };
