export const QuestionType = {
  Text: 'text',
  Textarea: 'textarea',
  Radio: 'radio',
  Select: 'select',
  Checkbox: 'checkbox',
  Number: 'number',
  Boolean: 'boolean',
  Stars: 'stars',
  DatetimePoll: 'datetime_poll',
  Section: 'section',
} as const;

export type QuestionType = (typeof QuestionType)[keyof typeof QuestionType];
