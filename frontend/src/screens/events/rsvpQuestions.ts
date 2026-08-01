/** Draft / wire-aligned RSVP question helpers used by authoring + RSVP dialog. */

import {
  questionTypeWantsOptions,
  RSVP_QUESTION_TYPE_OPTIONS,
  type RsvpQuestionType,
} from '@/components/questions/questionTypeOptions';
import { type Event, type EventRsvpQuestion, RsvpServerStatus } from '@/models/event';

export type { RsvpQuestionType };
export type RsvpQuestionDraft = EventRsvpQuestion;
export type RsvpAnswerValue = string;

const RESPONDENT_STATUSES = new Set<string>([
  RsvpServerStatus.Attending,
  RsvpServerStatus.Maybe,
  RsvpServerStatus.Waitlisted,
]);

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

export function isRsvpRespondentStatus(status: string): boolean {
  return RESPONDENT_STATUSES.has(status);
}

export function hasSavedRsvpAnswers(event: Event): boolean {
  return event.guests.some(
    (guest) => isRsvpRespondentStatus(guest.status) && Object.keys(guest.answers).length > 0,
  );
}

export function newQuestionId(): string {
  return `q-${crypto.randomUUID()}`;
}

export { questionTypeWantsOptions as wantsOptions };
