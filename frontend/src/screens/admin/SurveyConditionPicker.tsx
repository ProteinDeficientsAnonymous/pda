import { QuestionType } from '@/api/questionTypes';
import { type ShowIfCondition, ShowIfOperator, type SurveyQuestion } from '@/api/surveyAdmin';
import {
  conditionValues,
  eligibleSourceQuestions,
  operatorsFor,
} from '@/components/questions/questionVisibility';
import { Select } from '@/components/ui/Select';

const OPERATOR_LABELS: Record<ShowIfOperator, string> = {
  [ShowIfOperator.Equals]: 'is',
  [ShowIfOperator.NotEquals]: 'is not',
  [ShowIfOperator.Contains]: 'includes',
};

function operatorLabel(op: ShowIfOperator, fieldType: QuestionType): string {
  if (fieldType === QuestionType.Checkbox && op === ShowIfOperator.NotEquals) {
    return "doesn't include";
  }
  return OPERATOR_LABELS[op];
}

interface Props {
  questions: SurveyQuestion[];
  /** the question being edited, if any — only questions above it are eligible */
  editing?: SurveyQuestion | undefined;
  value: ShowIfCondition | null;
  onChange: (next: ShowIfCondition | null) => void;
}

export function SurveyConditionPicker({ questions, editing, value, onChange }: Props) {
  const eligible = eligibleSourceQuestions(questions, editing);
  const source = eligible.find((q) => q.id === value?.questionId);

  function defaultCondition(question: SurveyQuestion): ShowIfCondition {
    return {
      questionId: question.id,
      operator: operatorsFor(question.fieldType)[0] ?? ShowIfOperator.Equals,
      value: conditionValues(question)[0] ?? '',
    };
  }

  if (eligible.length === 0 && value === null) return null;

  const idPrefix = editing?.id ?? 'new';

  return (
    <div className="flex flex-col gap-2">
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={value !== null}
          onChange={(e) => {
            const first = eligible[0];
            onChange(e.target.checked && first ? defaultCondition(first) : null);
          }}
        />
        <span>only show when</span>
      </label>

      {value !== null && !source ? (
        <p className="text-muted text-xs">
          this condition points at a question that can no longer be a source — untick to clear it
        </p>
      ) : null}

      {value !== null && source ? (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-[2fr_1fr_1fr]">
          <Select
            id={`${idPrefix}-condition-question`}
            label="condition question"
            hideLabel
            value={value.questionId}
            onChange={(e) => {
              const next = eligible.find((q) => q.id === e.target.value);
              if (next) onChange(defaultCondition(next));
            }}
            options={eligible.map((q) => ({ value: q.id, label: q.label.toLowerCase() }))}
          />
          <Select
            id={`${idPrefix}-condition-operator`}
            label="condition"
            hideLabel
            value={value.operator}
            onChange={(e) => {
              onChange({ ...value, operator: e.target.value as ShowIfOperator });
            }}
            options={operatorsFor(source.fieldType).map((op) => ({
              value: op,
              label: operatorLabel(op, source.fieldType),
            }))}
          />
          <Select
            id={`${idPrefix}-condition-answer`}
            label="condition answer"
            hideLabel
            value={value.value}
            onChange={(e) => {
              onChange({ ...value, value: e.target.value });
            }}
            options={conditionValues(source).map((v) => ({ value: v, label: v.toLowerCase() }))}
          />
        </div>
      ) : null}
    </div>
  );
}
