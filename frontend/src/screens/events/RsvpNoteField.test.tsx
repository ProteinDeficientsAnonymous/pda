import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { RSVP_NOTE_MAX_LENGTH, RsvpNoteField } from './RsvpNoteField';

describe('RsvpNoteField', () => {
  it('renders the current value', () => {
    render(<RsvpNoteField value="hello" onChange={() => {}} />);
    expect(screen.getByRole('textbox')).toHaveValue('hello');
  });

  it('calls onChange as the user types', () => {
    const onChange = vi.fn();
    render(<RsvpNoteField value="" onChange={onChange} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'hi' } });
    expect(onChange).toHaveBeenCalledWith('hi');
  });

  it('shows remaining characters', () => {
    render(<RsvpNoteField value="ab" onChange={() => {}} />);
    expect(screen.getByText(`${RSVP_NOTE_MAX_LENGTH - 2} characters left`)).toBeInTheDocument();
  });
});
