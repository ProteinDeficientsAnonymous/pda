import type { JoinQuestionType } from '@/api/join';
import {
  QUESTION_TYPE_OPTION_BY_TYPE,
  type QuestionTypeOption,
} from '@/components/questions/questionTypeOptions';

const JOIN_QUESTION_TYPE_OPTION_BY_TYPE = {
  text: QUESTION_TYPE_OPTION_BY_TYPE.text,
  textarea: QUESTION_TYPE_OPTION_BY_TYPE.textarea,
  select: QUESTION_TYPE_OPTION_BY_TYPE.select,
} satisfies Record<JoinQuestionType, QuestionTypeOption>;

export const JOIN_QUESTION_TYPE_OPTIONS = Object.values(JOIN_QUESTION_TYPE_OPTION_BY_TYPE);
