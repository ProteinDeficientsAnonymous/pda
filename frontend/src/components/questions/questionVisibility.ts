import { QuestionType } from '@/api/questionTypes';
import {
  type AnswerValue,
  type ShowIfCondition,
  ShowIfOperator,
  type SurveyQuestion,
} from '@/api/surveys';

import { checkboxValues } from './checkboxAnswer';

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
    ? [ShowIfOperator.Contains, ShowIfOperator.NotEquals]
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

function conditionMet(
  answer: AnswerValue | undefined,
  condition: ShowIfCondition,
  multi: boolean,
): boolean {
  if (multi) {
    const ticked = checkboxValues(answer).includes(condition.value);
    return condition.operator === ShowIfOperator.NotEquals ? !ticked : ticked;
  }
  const single = typeof answer === 'string' ? answer : '';
  if (condition.operator === ShowIfOperator.NotEquals) return single !== condition.value;
  return single === condition.value;
}

/** mirrors the server evaluator: a condition on a hidden question is never met, so hiding cascades */
export function visibleQuestionIds(
  questions: readonly SurveyQuestion[],
  answers: Record<string, AnswerValue>,
): Set<string> {
  const visible = new Set<string>();
  const ordered = [...questions].sort((a, b) => a.displayOrder - b.displayOrder);
  const types = new Map(questions.map((q) => [q.id, q.fieldType]));
  for (const q of ordered) {
    if (!q.showIf) {
      visible.add(q.id);
      continue;
    }
    if (!visible.has(q.showIf.questionId)) continue;
    const answer = answers[q.showIf.questionId];
    const multi = types.get(q.showIf.questionId) === QuestionType.Checkbox;
    if (conditionMet(answer, q.showIf, multi)) {
      visible.add(q.id);
    }
  }
  return visible;
}
