import type { QuestionType } from '@/api/questionTypes';

export interface QuestionTypeOption {
  value: QuestionType;
  label: string;
  wantsOptions: boolean;
}

/** Canonical authoring metadata for every catalog question type. */
export const QUESTION_TYPE_OPTION_BY_TYPE = {
  text: { value: 'text', label: 'short text', wantsOptions: false },
  textarea: { value: 'textarea', label: 'long text', wantsOptions: false },
  number: { value: 'number', label: 'number', wantsOptions: false },
  radio: { value: 'radio', label: 'radio', wantsOptions: true },
  select: { value: 'select', label: 'select', wantsOptions: true },
  checkbox: { value: 'checkbox', label: 'checkbox', wantsOptions: true },
  boolean: { value: 'boolean', label: 'yes / no', wantsOptions: false },
  rating: { value: 'rating', label: '1–5 rating', wantsOptions: true },
  datetime_poll: {
    value: 'datetime_poll',
    label: 'datetime poll (iso options)',
    wantsOptions: true,
  },
} satisfies Record<QuestionType, QuestionTypeOption>;

/** Full-catalog authoring list (used by survey; survey ⊆ catalog is currently equal). */
export const QUESTION_TYPE_OPTIONS = Object.values(QUESTION_TYPE_OPTION_BY_TYPE);

export function questionTypeWantsOptions(fieldType: QuestionType): boolean {
  return QUESTION_TYPE_OPTION_BY_TYPE[fieldType].wantsOptions;
}

export function questionOptionsError(
  wantsOptions: boolean,
  options: readonly string[],
): string | null {
  return wantsOptions && options.length === 0 ? 'add at least one option' : null;
}
