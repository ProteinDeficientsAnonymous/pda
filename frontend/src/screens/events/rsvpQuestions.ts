import { newRsvpQuestionId, type RsvpQuestionType } from '@/api/eventRsvpQuestions';
import {
  questionTypeWantsOptions,
  RSVP_QUESTION_TYPE_OPTIONS,
} from '@/components/questions/questionTypeOptions';
import { type Event, type EventRsvpQuestion, RsvpServerStatus } from '@/models/event';

export type { RsvpQuestionType };
export type RsvpQuestionDraft = EventRsvpQuestion;
export type RsvpAnswerValue = string;

export { RSVP_QUESTION_TYPE_OPTIONS };
export { newRsvpQuestionId as newQuestionId };

const RESPONDENT_STATUSES = new Set<string>([
  RsvpServerStatus.Attending,
  RsvpServerStatus.Waitlisted,
]);

export const RSVP_QUESTION_TYPE_LABELS: Record<RsvpQuestionType, string> = Object.fromEntries(
  RSVP_QUESTION_TYPE_OPTIONS.map((o) => [o.value, o.label]),
) as Record<RsvpQuestionType, string>;

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

export function rsvpQuestionsApplyToStatus(status: string): boolean {
  return RESPONDENT_STATUSES.has(status);
}

export function shouldShowRsvpQuestions({
  status,
  questionCount,
  mode,
  changedFromInitial,
}: {
  status: string;
  questionCount: number;
  mode: 'create' | 'edit';
  changedFromInitial: boolean;
}): boolean {
  if (questionCount === 0) return false;
  if (rsvpQuestionsApplyToStatus(status)) return true;
  if (status !== RsvpServerStatus.Maybe) return false;
  if (mode === 'create') return true;
  return changedFromInitial;
}

export function guestShowsQuestionnaire(status: string, responseCount: number): boolean {
  if (isRsvpRespondentStatus(status)) return true;
  return status === RsvpServerStatus.Maybe && responseCount > 0;
}

export function hasQuestionHistory(event: Event): boolean {
  return event.rsvpQuestions.length > 0 || hasSavedQuestionnaireResponses(event);
}

export function hasSavedQuestionnaireResponses(event: Event): boolean {
  return event.guests.some((guest) => {
    const responseCount = Object.keys(guest.questionnaireResponses).length;
    return responseCount > 0 && guestShowsQuestionnaire(guest.status, responseCount);
  });
}

export { questionTypeWantsOptions as wantsOptions };
