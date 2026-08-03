import type { JoinQuestionType } from '@/api/join';
import type { SurveyQuestionType } from '@/api/surveys';

interface QuestionTypeOption {
  value: SurveyQuestionType;
  label: string;
  wantsOptions: boolean;
}

const QUESTION_TYPE_OPTION_BY_TYPE = {
  text: { value: 'text', label: 'short text', wantsOptions: false },
  textarea: { value: 'textarea', label: 'long text', wantsOptions: false },
  number: { value: 'number', label: 'number', wantsOptions: false },
  select: { value: 'select', label: 'single choice (radio)', wantsOptions: true },
  dropdown: { value: 'dropdown', label: 'dropdown', wantsOptions: true },
  multiselect: { value: 'multiselect', label: 'multiple choice', wantsOptions: true },
  yes_no: { value: 'yes_no', label: 'yes / no', wantsOptions: false },
  rating: { value: 'rating', label: '1–5 rating', wantsOptions: true },
  datetime_poll: {
    value: 'datetime_poll',
    label: 'datetime poll (iso options)',
    wantsOptions: true,
  },
} satisfies Record<SurveyQuestionType, QuestionTypeOption>;

/** Canonical authoring metadata for question types. */
export const QUESTION_TYPE_OPTIONS = Object.values(QUESTION_TYPE_OPTION_BY_TYPE);

const JOIN_QUESTION_TYPE_OPTION_BY_TYPE = {
  text: QUESTION_TYPE_OPTION_BY_TYPE.text,
  textarea: QUESTION_TYPE_OPTION_BY_TYPE.textarea,
  dropdown: QUESTION_TYPE_OPTION_BY_TYPE.dropdown,
} satisfies Record<JoinQuestionType, QuestionTypeOption>;

export const JOIN_QUESTION_TYPE_OPTIONS = Object.values(JOIN_QUESTION_TYPE_OPTION_BY_TYPE);

export function questionTypeWantsOptions(fieldType: SurveyQuestionType): boolean {
  return QUESTION_TYPE_OPTION_BY_TYPE[fieldType].wantsOptions;
}

export function questionOptionsError(
  wantsOptions: boolean,
  options: readonly string[],
): string | null {
  return wantsOptions && options.length === 0 ? 'add at least one option for this' : null;
}
