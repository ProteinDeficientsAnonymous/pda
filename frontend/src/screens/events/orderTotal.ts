import { QuestionType } from '@/api/questionTypes';
import { checkboxValues } from '@/components/questions/checkboxAnswer';
import type { EventRsvpQuestion, QuestionnaireAnswer, QuestionnaireSnapshot } from '@/models/event';

type Answers = Readonly<Record<string, QuestionnaireAnswer | undefined>>;

export function isPricedQuestion(question: EventRsvpQuestion): boolean {
  return Boolean(question.optionPrices?.length);
}

export function answerPriceCents(
  question: EventRsvpQuestion,
  answer: QuestionnaireAnswer | undefined,
): number {
  const prices = question.optionPrices ?? [];
  if (prices.length === 0 || answer === undefined) return 0;
  const chosen =
    question.fieldType === QuestionType.Checkbox ? checkboxValues(answer) : [String(answer).trim()];
  return chosen.reduce((sum, option) => sum + (prices[question.options.indexOf(option)] ?? 0), 0);
}

/** return(null): no priced question, so the event's own price applies. */
export function orderTotalCents(
  questions: readonly EventRsvpQuestion[],
  answers: Answers,
): number | null {
  const priced = questions.filter(isPricedQuestion);
  if (priced.length === 0) return null;
  return priced.reduce((sum, q) => sum + answerPriceCents(q, answers[q.id]), 0);
}

/** Saved answers keep the price they were ordered at; ones saved before pricing use today's. */
export function savedOrderTotalCents(
  questions: readonly EventRsvpQuestion[],
  responses: Readonly<Record<string, QuestionnaireSnapshot>>,
): number | null {
  const byId = new Map(questions.map((q) => [q.id, q]));
  let total = questions.some(isPricedQuestion) ? 0 : null;
  for (const [id, snap] of Object.entries(responses)) {
    const question = byId.get(id);
    const cents =
      snap.priceCents ??
      (question && isPricedQuestion(question) ? answerPriceCents(question, snap.answer) : null);
    if (cents !== null) total = (total ?? 0) + cents;
  }
  return total;
}
