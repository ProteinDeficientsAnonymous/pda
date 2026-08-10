export const QuestionType = {
  Text: 'text',
  Textarea: 'textarea',
  Radio: 'radio',
  Select: 'select',
  Checkbox: 'checkbox',
  Number: 'number',
  Boolean: 'boolean',
  Rating: 'rating',
  DatetimePoll: 'datetime_poll',
} as const;

export type QuestionType = (typeof QuestionType)[keyof typeof QuestionType];
