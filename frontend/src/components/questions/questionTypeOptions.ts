import type { SurveyQuestionType } from '@/api/surveys';

/** Canonical authoring metadata for survey/RSVP question types (shared UX labels). */
export const QUESTION_TYPE_OPTIONS: {
  value: SurveyQuestionType;
  label: string;
  wantsOptions: boolean;
}[] = [
  { value: 'text', label: 'short text', wantsOptions: false },
  { value: 'textarea', label: 'long text', wantsOptions: false },
  { value: 'number', label: 'number', wantsOptions: false },
  { value: 'select', label: 'single choice (radio)', wantsOptions: true },
  { value: 'dropdown', label: 'dropdown', wantsOptions: true },
  { value: 'multiselect', label: 'multiple choice', wantsOptions: true },
  { value: 'yes_no', label: 'yes / no', wantsOptions: false },
  { value: 'rating', label: '1–5 rating', wantsOptions: true },
  { value: 'datetime_poll', label: 'datetime poll (iso options)', wantsOptions: true },
];

/** Subset hosts can attach to event RSVPs — same wire values as surveys. */
export type RsvpQuestionType = 'textarea' | 'dropdown' | 'multiselect';

export const RSVP_QUESTION_TYPE_OPTIONS: {
  value: RsvpQuestionType;
  label: string;
  wantsOptions: boolean;
}[] = [
  { value: 'textarea', label: 'long text', wantsOptions: false },
  { value: 'dropdown', label: 'dropdown', wantsOptions: true },
  { value: 'multiselect', label: 'multiple choice', wantsOptions: true },
];

export function questionTypeWantsOptions(fieldType: SurveyQuestionType): boolean {
  return QUESTION_TYPE_OPTIONS.find((o) => o.value === fieldType)?.wantsOptions ?? false;
}
