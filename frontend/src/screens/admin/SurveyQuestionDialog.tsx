import { QuestionType } from '@/api/questionTypes';
import {
  type SurveyQuestion,
  type SurveyQuestionInput,
  type SurveyQuestionType,
  useCreateSurveyQuestion,
  useUpdateSurveyQuestion,
} from '@/api/surveyAdmin';
import { DEFAULT_SURVEY_QUESTION_TYPE } from '@/api/surveys';
import { QuestionAuthorDialog } from '@/components/questions/QuestionAuthorDialog';
import { QUESTION_TYPE_OPTIONS } from '@/components/questions/questionTypeOptions';

interface Props {
  surveyId: string;
  open: boolean;
  onClose: () => void;
  existing?: SurveyQuestion | undefined;
}

export function SurveyQuestionDialog(props: Props) {
  if (!props.open) return null;
  return <SurveyQuestionDialogBody key={props.existing?.id ?? 'new'} {...props} />;
}

function SurveyQuestionDialogBody({ surveyId, open, onClose, existing }: Props) {
  const create = useCreateSurveyQuestion(surveyId);
  const update = useUpdateSurveyQuestion(surveyId, existing?.id ?? '');
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
      busy={busy}
      onSave={async (values) => {
        const input: SurveyQuestionInput = {
          label: values.label,
          fieldType: values.fieldType,
          options: values.options,
          required: values.required,
        };
        if (existing) await update.mutateAsync(input);
        else await create.mutateAsync(input);
      }}
    />
  );
}
