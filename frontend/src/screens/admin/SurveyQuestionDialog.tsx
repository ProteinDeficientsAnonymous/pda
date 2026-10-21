import { useState } from 'react';

import { QuestionType } from '@/api/questionTypes';
import {
  type ShowIfCondition,
  type SurveyQuestion,
  type SurveyQuestionInput,
  type SurveyQuestionType,
  useCreateSurveyQuestion,
  useUpdateSurveyQuestion,
} from '@/api/surveyAdmin';
import { DEFAULT_SURVEY_QUESTION_TYPE } from '@/api/surveys';
import { QuestionAuthorDialog } from '@/components/questions/QuestionAuthorDialog';
import { QUESTION_TYPE_OPTIONS } from '@/components/questions/questionTypeOptions';

import { SurveyConditionPicker } from './SurveyConditionPicker';

interface Props {
  surveyId: string;
  open: boolean;
  onClose: () => void;
  questions: SurveyQuestion[];
  existing?: SurveyQuestion | undefined;
}

export function SurveyQuestionDialog(props: Props) {
  if (!props.open) return null;
  return <SurveyQuestionDialogBody key={props.existing?.id ?? 'new'} {...props} />;
}

function SurveyQuestionDialogBody({ surveyId, open, onClose, questions, existing }: Props) {
  const create = useCreateSurveyQuestion(surveyId);
  const update = useUpdateSurveyQuestion(surveyId, existing?.id ?? '');
  const [showIf, setShowIf] = useState<ShowIfCondition | null>(() => existing?.showIf ?? null);
  const busy = create.isPending || update.isPending;

  return (
    <QuestionAuthorDialog<SurveyQuestionType>
      open={open}
      onClose={onClose}
      title={existing ? 'edit question' : 'add question'}
      initial={{
        label: existing?.label ?? '',
        fieldType: existing?.fieldType ?? DEFAULT_SURVEY_QUESTION_TYPE,
        options: existing?.options ?? [],
        required: existing?.required ?? false,
      }}
      typeOptions={QUESTION_TYPE_OPTIONS.map((t) => ({ value: t.value, label: t.label }))}
      optionsHint={(fieldType) =>
        fieldType === QuestionType.Rating
          ? 'up to 5 star labels'
          : fieldType === QuestionType.DatetimePoll
            ? 'ISO-8601 datetime values'
            : undefined
      }
      extraFields={
        <SurveyConditionPicker
          questions={questions}
          editing={existing}
          value={showIf}
          onChange={setShowIf}
        />
      }
      busy={busy}
      onSave={async (values) => {
        const input: SurveyQuestionInput = {
          label: values.label,
          fieldType: values.fieldType,
          options: values.options,
          required: values.required,
          showIf,
        };
        if (existing) await update.mutateAsync(input);
        else await create.mutateAsync(input);
      }}
    />
  );
}
