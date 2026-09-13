import { QuestionType } from '@/api/questionTypes';
import {
  type AnswerValue,
  type ShowIfCondition,
  ShowIfOperator,
  type SurveyQuestion,
} from '@/api/surveys';

/** question types whose answers a condition can be written against */
export const CONDITION_SOURCE_TYPES: readonly QuestionType[] = [
  QuestionType.Radio,
  QuestionType.Select,
  QuestionType.Checkbox,
  QuestionType.Boolean,
];

export const BOOLEAN_CONDITION_VALUES = ['yes', 'no'];

export function canBeConditionSource(fieldType: QuestionType): boolean {
  return CONDITION_SOURCE_TYPES.includes(fieldType);
}

/** values a condition on this question may compare against */
export function conditionValues(question: Pick<SurveyQuestion, 'fieldType' | 'options'>): string[] {
  return question.fieldType === QuestionType.Boolean
    ? [...BOOLEAN_CONDITION_VALUES]
    : question.options;
}

export function operatorsFor(fieldType: QuestionType): ShowIfOperator[] {
  return fieldType === QuestionType.Checkbox
    ? [ShowIfOperator.Equals, ShowIfOperator.NotEquals, ShowIfOperator.Contains]
    : [ShowIfOperator.Equals, ShowIfOperator.NotEquals];
}

/** questions a condition on the question being edited may point at */
export function eligibleSourceQuestions(
  questions: readonly SurveyQuestion[],
  editing?: SurveyQuestion,
): SurveyQuestion[] {
  return questions
    .filter((q) => canBeConditionSource(q.fieldType))
    .filter((q) => (editing ? q.displayOrder < editing.displayOrder : true))
    .sort((a, b) => a.displayOrder - b.displayOrder);
}

function conditionMet(answer: string, condition: ShowIfCondition): boolean {
  if (condition.operator === ShowIfOperator.Contains) {
    return answer
      .split(',')
      .map((v) => v.trim())
      .filter(Boolean)
      .includes(condition.value);
  }
  if (condition.operator === ShowIfOperator.NotEquals) return answer !== condition.value;
  return answer === condition.value;
}

/**
 * Ids of the questions a respondent should see. Mirrors the server evaluator —
 * a condition pointing at a hidden question is never met, so hiding cascades.
 */
export function visibleQuestionIds(
  questions: readonly SurveyQuestion[],
  answers: Record<string, AnswerValue>,
): Set<string> {
  const visible = new Set<string>();
  const ordered = [...questions].sort((a, b) => a.displayOrder - b.displayOrder);
  for (const q of ordered) {
    if (!q.showIf) {
      visible.add(q.id);
      continue;
    }
    if (!visible.has(q.showIf.questionId)) continue;
    const answer = answers[q.showIf.questionId];
    if (conditionMet(typeof answer === 'string' ? answer : '', q.showIf)) {
      visible.add(q.id);
    }
  }
  return visible;
}
