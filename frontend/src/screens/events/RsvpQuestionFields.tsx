import { QuestionField } from '@/components/questions/QuestionField';
import { formatCents } from '@/utils/orderPrice';

import { isPricedQuestion, orderTotalCents } from './orderTotal';
import type { RsvpAnswerValue, RsvpQuestionDraft } from './rsvpQuestions';

interface Props {
  questions: readonly RsvpQuestionDraft[];
  answers: Readonly<Record<string, RsvpAnswerValue | undefined>>;
  onChange: (questionId: string, value: RsvpAnswerValue) => void;
  errors: Readonly<Record<string, string | undefined>>;
  disabled?: boolean;
}

/** RSVP answers reuse the shared QuestionField so survey/RSVP UX stays aligned. */
export function RsvpQuestionFields({
  questions,
  answers,
  onChange,
  errors,
  disabled = false,
}: Props) {
  if (questions.length === 0) return null;
  const total = orderTotalCents(questions, answers);

  return (
    <div className="flex flex-col gap-4">
      {questions.map((question) => (
        <div key={question.id} className="flex flex-col gap-1">
          <QuestionField
            question={question}
            value={answers[question.id] ?? ''}
            onChange={(v) => {
              onChange(question.id, typeof v === 'string' || Array.isArray(v) ? v : '');
            }}
            error={errors[question.id]}
            readOnly={disabled}
          />
          {isPricedQuestion(question) ? (
            <p className="text-muted text-xs">{optionPriceList(question)}</p>
          ) : null}
        </div>
      ))}
      {total === null ? null : (
        <p className="text-foreground text-sm font-medium">your total: {formatCents(total)}</p>
      )}
    </div>
  );
}

function optionPriceList(question: RsvpQuestionDraft): string {
  return question.options
    .map((option, i) => `${option} ${formatCents(question.optionPrices?.[i] ?? 0)}`)
    .join(' · ');
}
