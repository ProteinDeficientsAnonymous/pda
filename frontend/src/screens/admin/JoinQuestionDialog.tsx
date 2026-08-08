import type { JoinQuestion, JoinQuestionInput, JoinQuestionType } from '@/api/join';
import {
  DEFAULT_JOIN_QUESTION_TYPE,
  useCreateJoinQuestion,
  useUpdateJoinQuestion,
} from '@/api/join';
import { QuestionAuthorDialog } from '@/components/questions/QuestionAuthorDialog';
import { JOIN_QUESTION_TYPE_OPTIONS } from '@/components/questions/questionTypeOptions';

interface Props {
  open: boolean;
  onClose: () => void;
  /** If set, the dialog is in edit mode. */
  existing?: JoinQuestion | undefined;
}

export function JoinQuestionDialog(props: Props) {
  if (!props.open) return null;
  return <JoinQuestionDialogBody key={props.existing?.id ?? 'new'} {...props} />;
}

function JoinQuestionDialogBody({ open, onClose, existing }: Props) {
  const create = useCreateJoinQuestion();
  const update = useUpdateJoinQuestion(existing?.id ?? '');
  const busy = create.isPending || update.isPending;

  return (
    <QuestionAuthorDialog<JoinQuestionType>
      open={open}
      onClose={onClose}
      title={existing ? 'edit question' : 'add question'}
      initial={{
        label: existing?.label ?? '',
        fieldType: existing?.fieldType ?? DEFAULT_JOIN_QUESTION_TYPE,
        options: existing?.options ?? [],
        required: existing?.required ?? false,
      }}
      typeOptions={JOIN_QUESTION_TYPE_OPTIONS}
      busy={busy}
      onSave={async (values) => {
        const input: JoinQuestionInput = {
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
