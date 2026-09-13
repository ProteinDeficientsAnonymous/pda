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
      operator: ShowIfOperator.Equals,
      value: conditionValues(question)[0] ?? '',
    };
  }

  if (eligible.length === 0) {
    return (
      <p className="text-muted text-xs">
        add a choice or yes/no question above this one to make it conditional
      </p>
    );
  }

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

      {value !== null && source ? (
        <div className="border-border flex flex-col gap-2 rounded-md border p-3">
          <Select
            label="question"
            value={value.questionId}
            onChange={(e) => {
              const next = eligible.find((q) => q.id === e.target.value);
              if (next) onChange(defaultCondition(next));
            }}
            options={eligible.map((q) => ({ value: q.id, label: q.label.toLowerCase() }))}
          />
          <Select
            label="condition"
            value={value.operator}
            onChange={(e) => {
              onChange({ ...value, operator: e.target.value as ShowIfOperator });
            }}
            options={operatorsFor(source.fieldType).map((op) => ({
              value: op,
              label: OPERATOR_LABELS[op],
            }))}
          />
          <Select
            label="answer"
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
