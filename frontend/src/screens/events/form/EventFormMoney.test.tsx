import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { emptyEventFormValues } from '@/api/eventWrites';

import { EventFormMoney } from './EventFormLinksAndCost';

describe('EventFormMoney', () => {
  it('edits the price note', () => {
    const onChange = vi.fn();
    render(
      <EventFormMoney
        values={{ ...emptyEventFormValues(), priceNote: 'deposit' }}
        onChange={onChange}
        errors={{}}
      />,
    );
    const note = screen.getByLabelText('price note');
    expect(note).toHaveValue('deposit');
    fireEvent.change(note, { target: { value: 'sliding scale $6–$8' } });
    expect(onChange).toHaveBeenCalledWith({ priceNote: 'sliding scale $6–$8' });
  });
});
