/** Draft / wire-aligned RSVP question shape used by authoring + RSVP dialog. */

export type RsvpQuestionType = 'free_response' | 'select_one' | 'select_multiple';

export interface RsvpQuestionDraft {
  id: string;
  label: string;
  fieldType: RsvpQuestionType;
  options: string[];
  required: boolean;
}

/** Free text, single selected option, or multi-select list. */
export type RsvpAnswerValue = string | string[];

export const RSVP_QUESTION_TYPE_LABELS: Record<RsvpQuestionType, string> = {
  free_response: 'free response',
  select_one: 'select one',
  select_multiple: 'select multiple',
};

export function rsvpSectionSummary(rsvpEnabled: boolean): string | undefined {
  return rsvpEnabled ? 'enabled' : undefined;
}

export function questionsSectionSummary(questionCount: number): string | undefined {
  if (questionCount === 0) return undefined;
  return `${String(questionCount)} question${questionCount === 1 ? '' : 's'}`;
}

export function wantsOptions(fieldType: RsvpQuestionType): boolean {
  return fieldType === 'select_one' || fieldType === 'select_multiple';
}

export function parseOptionsText(text: string): string[] {
  return text
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
}

export function isAnswerFilled(value: RsvpAnswerValue | undefined): boolean {
  if (value === undefined) return false;
  if (Array.isArray(value)) return value.length > 0;
  return value.trim().length > 0;
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
