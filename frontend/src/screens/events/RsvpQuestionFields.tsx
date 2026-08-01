import type { AnswerValue, SurveyQuestion } from '@/api/surveys';
import { QuestionField } from '@/components/questions/QuestionField';

import type { RsvpAnswerValue, RsvpQuestionDraft, RsvpQuestionType } from './rsvpQuestions';

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
          value={toSurveyValue(question.fieldType, answers[question.id])}
          onChange={(v) => {
            onChange(question.id, fromSurveyValue(question.fieldType, v));
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

function toSurveyValue(
  fieldType: RsvpQuestionType,
  value: RsvpAnswerValue | undefined,
): AnswerValue | undefined {
  if (value === undefined) return undefined;
  if (fieldType === 'multiselect') {
    return Array.isArray(value) ? value.join(',') : value;
  }
  return typeof value === 'string' ? value : '';
}

function fromSurveyValue(fieldType: RsvpQuestionType, value: AnswerValue): RsvpAnswerValue {
  if (fieldType === 'multiselect') {
    if (typeof value !== 'string' || !value) return [];
    return value.split(',').filter(Boolean);
  }
  return typeof value === 'string' ? value : '';
}
