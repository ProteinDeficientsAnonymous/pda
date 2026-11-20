import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { QuestionType } from '@/api/questionTypes';
import { RsvpServerStatus } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

import { MyOrderTotal } from './MyOrderTotal';

const meal = {
  id: 'meal',
  label: 'meal',
  fieldType: QuestionType.Select,
  options: ['bowl', 'plate'],
  optionPrices: [1200, 1850],
  required: true,
};
const myAnswer = { meal: { label: 'meal', answer: 'plate', priceCents: 1850 } };

describe('MyOrderTotal', () => {
  it('shows the total of what i ordered', () => {
    const event = makeEvent({
      myRsvp: RsvpServerStatus.Attending,
      rsvpQuestions: [meal],
      myQuestionnaireResponses: myAnswer,
    });
    render(<MyOrderTotal event={event} />);
    expect(screen.getByText('your order: $18.50')).toBeInTheDocument();
  });

  it("hides once i can't go", () => {
    const event = makeEvent({
      myRsvp: RsvpServerStatus.CantGo,
      rsvpQuestions: [meal],
      myQuestionnaireResponses: myAnswer,
    });
    const { container } = render(<MyOrderTotal event={event} />);
    expect(container).toBeEmptyDOMElement();
  });
});
