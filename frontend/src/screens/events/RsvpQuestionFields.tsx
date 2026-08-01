import type { SurveyQuestion } from '@/api/surveys';
import { QuestionField } from '@/components/questions/QuestionField';

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

  return (
    <div className="flex flex-col gap-4">
      {questions.map((question) => (
        <QuestionField
          key={question.id}
          question={toSurveyQuestion(question)}
          value={answers[question.id] ?? ''}
          onChange={(v) => {
            onChange(question.id, typeof v === 'string' ? v : '');
          }}
          error={errors[question.id]}
          readOnly={disabled}
        />
      ))}
    </div>
  );
}

function toSurveyQuestion(q: RsvpQuestionDraft): SurveyQuestion {
  return {
    id: q.id,
    label: q.label,
    fieldType: q.fieldType,
    options: q.options,
    required: q.required,
    displayOrder: 0,
  };
}
