import type { SurveyQuestionType } from '@/api/surveys';

/** Canonical authoring metadata for question types. */
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

export function questionTypeWantsOptions(fieldType: SurveyQuestionType): boolean {
  return QUESTION_TYPE_OPTIONS.find((o) => o.value === fieldType)?.wantsOptions ?? false;
}
