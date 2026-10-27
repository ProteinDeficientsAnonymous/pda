import type { RsvpQuestionType } from '@/api/eventRsvpQuestions';
import type { JoinQuestionType } from '@/api/join';
import { QuestionType } from '@/api/questionTypes';

export interface QuestionTypeOption {
  value: QuestionType;
  label: string;
  wantsOptions: boolean;
}

/** Labels / option-requirement flags keyed by catalog wire value. */
const QUESTION_TYPE_META: Record<QuestionType, Omit<QuestionTypeOption, 'value'>> = {
  [QuestionType.Text]: { label: 'short text', wantsOptions: false },
  [QuestionType.Textarea]: { label: 'long answer', wantsOptions: false },
  [QuestionType.Number]: { label: 'number', wantsOptions: false },
  [QuestionType.Radio]: { label: 'radio', wantsOptions: true },
  [QuestionType.Select]: { label: 'select', wantsOptions: true },
  [QuestionType.Checkbox]: { label: 'checkbox', wantsOptions: true },
  [QuestionType.Boolean]: { label: 'yes / no', wantsOptions: false },
  [QuestionType.Stars]: { label: 'star rating', wantsOptions: false },
  [QuestionType.Scale]: { label: '1–5 scale', wantsOptions: false },
  [QuestionType.DatetimePoll]: { label: 'datetime poll', wantsOptions: true },
  [QuestionType.Section]: { label: 'section header', wantsOptions: false },
};

/** Canonical authoring metadata for every catalog question type. */
export const QUESTION_TYPE_OPTION_BY_TYPE = Object.fromEntries(
  (Object.values(QuestionType) as QuestionType[]).map((value) => [
    value,
    { value, ...QUESTION_TYPE_META[value] },
  ]),
) as Record<QuestionType, QuestionTypeOption>;

/** Full-catalog authoring list (used by survey; survey ⊆ catalog is currently equal). */
export const QUESTION_TYPE_OPTIONS = Object.values(QUESTION_TYPE_OPTION_BY_TYPE);

const JOIN_QUESTION_TYPES = [
  QuestionType.Text,
  QuestionType.Textarea,
  QuestionType.Select,
] as const satisfies readonly JoinQuestionType[];

export type JoinQuestionTypeOption = QuestionTypeOption & { value: JoinQuestionType };

/** Join-form authoring subset, projected from the shared catalog metadata. */
export const JOIN_QUESTION_TYPE_OPTIONS: JoinQuestionTypeOption[] = JOIN_QUESTION_TYPES.map(
  (value) => ({ ...QUESTION_TYPE_OPTION_BY_TYPE[value], value }),
);

const RSVP_QUESTION_TYPES = [
  QuestionType.Textarea,
  QuestionType.Select,
  QuestionType.Checkbox,
] as const satisfies readonly RsvpQuestionType[];

export type RsvpQuestionTypeOption = QuestionTypeOption & { value: RsvpQuestionType };

/** RSVP authoring subset, projected from the shared catalog metadata. */
export const RSVP_QUESTION_TYPE_OPTIONS: RsvpQuestionTypeOption[] = RSVP_QUESTION_TYPES.map(
  (value) => ({ ...QUESTION_TYPE_OPTION_BY_TYPE[value], value }),
);

export function questionTypeWantsOptions(fieldType: QuestionType): boolean {
  return QUESTION_TYPE_OPTION_BY_TYPE[fieldType].wantsOptions;
}

export function questionOptionsError(
  wantsOptions: boolean,
  options: readonly string[],
): string | null {
  return wantsOptions && options.length === 0 ? 'add at least one option' : null;
}

export function normalizeQuestionOptions(options: readonly string[]): string[] {
  return options.map((option) => option.trim()).filter(Boolean);
}

export const RATING_SCALE_SIZE = 5;

/** [low, high] labels for the two ends of a 1–5 scale. */
export function scaleEndLabels(options: readonly string[]): [string, string] {
  return [options[0] ?? '', options[1] ?? ''];
}

export function labelsEveryScalePoint(options: readonly string[]): boolean {
  return options.length === RATING_SCALE_SIZE;
}

/** Label for each point 1–5: all five as given, or just the two ends. */
export function scaleLabels(options: readonly string[]): string[] {
  if (labelsEveryScalePoint(options)) return [...options];
  const [low, high] = scaleEndLabels(options);
  return [low, '', '', '', high];
}

/** Accessible name for a scale point, e.g. "5 — great" when that point is labeled. */
export function scalePointLabel(n: number, options: readonly string[]): string {
  const label = scaleLabels(options)[n - 1];
  return label ? `${String(n)} — ${label}` : String(n);
}

export function normalizeScaleEndLabels(options: readonly string[]): string[] {
  const labels = scaleEndLabels(options).map((label) => label.trim());
  return labels.some(Boolean) ? labels : [];
}
