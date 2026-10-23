import { useEffect, useRef, useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  type ShowIfCondition,
  type SurveyQuestion,
  type SurveyQuestionType,
  useUpdateSurveyQuestion,
} from '@/api/surveyAdmin';
import type { QuestionAuthorValues } from '@/components/questions/QuestionAuthorDialog';
import { QuestionCardEditor } from '@/components/questions/QuestionCardEditor';
import { QUESTION_TYPE_OPTIONS } from '@/components/questions/questionTypeOptions';

import { SurveyConditionPicker } from './SurveyConditionPicker';

const TYPE_OPTIONS = QUESTION_TYPE_OPTIONS.map((t) => ({ value: t.value, label: t.label }));

interface Props {
  surveyId: string;
  question: SurveyQuestion;
  questions: SurveyQuestion[];
  focusOnMount: boolean;
  locked: boolean;
  onDuplicate: () => void;
  onDelete: () => void;
}

export function SurveyQuestionCard({
  surveyId,
  question,
  questions,
  focusOnMount,
  locked,
  onDuplicate,
  onDelete,
}: Props) {
  const update = useUpdateSurveyQuestion(surveyId, question.id);
  const initial: QuestionAuthorValues = {
    label: question.label,
    fieldType: question.fieldType,
    options: question.options,
    required: question.required,
  };
  // Last-sent values, so a condition save during an in-flight label save keeps the new label.
  const latest = useRef(initial);
  const latestShowIf = useRef<ShowIfCondition | null>(question.showIf ?? null);
  const queue = useRef<Promise<unknown>>(Promise.resolve());
  const [showIf, setShowIf] = useState<ShowIfCondition | null>(question.showIf ?? null);
  const [serverShowIf, setServerShowIf] = useState(question.showIf ?? null);
  const [conditionError, setConditionError] = useState<string | null>(null);

  // Deleting a source question clears this condition server-side; follow it.
  if (JSON.stringify(question.showIf ?? null) !== JSON.stringify(serverShowIf)) {
    setServerShowIf(question.showIf ?? null);
    setShowIf(question.showIf ?? null);
  }

  useEffect(() => {
    latestShowIf.current = serverShowIf;
  }, [serverShowIf]);

  function enqueue(values: QuestionAuthorValues, condition: ShowIfCondition | null) {
    latest.current = values;
    latestShowIf.current = condition;
    const run = queue.current
      .catch(() => undefined)
      .then(() => update.mutateAsync({ ...values, showIf: condition }));
    queue.current = run;
    return run;
  }

  return (
    <QuestionCardEditor<SurveyQuestionType>
      id={question.id}
      value={initial}
      typeOptions={TYPE_OPTIONS}
      focusOnMount={focusOnMount}
      disabled={locked}
      onDuplicate={onDuplicate}
      onDelete={onDelete}
      onSave={(values) => enqueue(values, latestShowIf.current)}
      extraFields={
        locked ? null : (
          <div className="flex flex-col gap-1">
            <SurveyConditionPicker
              questions={questions}
              editing={question}
              value={showIf}
              onChange={(next) => {
                setShowIf(next);
                setConditionError(null);
                enqueue(latest.current, next).catch((err: unknown) => {
                  setConditionError(
                    extractApiErrorOr(err, "couldn't save the condition — try again"),
                  );
                });
              }}
            />
            {conditionError ? (
              <p role="alert" className="text-destructive text-xs">
                {conditionError}
              </p>
            ) : null}
          </div>
        )
      }
    />
  );
}
