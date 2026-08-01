import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { RsvpQuestionDraft } from '../rsvpQuestions';
import { EventRsvpQuestionDialog } from './EventRsvpQuestionDialog';

describe('EventRsvpQuestionDialog', () => {
  it('requires a question', () => {
    const onSave = vi.fn();
    render(<EventRsvpQuestionDialog open onClose={() => {}} onSave={onSave} />);
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/question required/i);
    expect(onSave).not.toHaveBeenCalled();
  });

  it('requires options for select one', () => {
    const onSave = vi.fn();
    render(<EventRsvpQuestionDialog open onClose={() => {}} onSave={onSave} />);
    fireEvent.change(screen.getByLabelText('question'), { target: { value: 'pick one' } });
    fireEvent.change(screen.getByLabelText('type'), { target: { value: 'dropdown' } });
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/at least one option/i);
    expect(onSave).not.toHaveBeenCalled();
  });

  it('saves a free response question', () => {
    const onSave = vi.fn();
    const onClose = vi.fn();
    render(<EventRsvpQuestionDialog open onClose={onClose} onSave={onSave} />);
    fireEvent.change(screen.getByLabelText('question'), { target: { value: 'notes' } });
    fireEvent.click(screen.getByLabelText('required'));
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        label: 'notes',
        fieldType: 'textarea',
        options: [],
        required: true,
        id: expect.any(String) as string,
      }),
    );
    expect(onClose).toHaveBeenCalled();
  });

  it('saves select multiple with parsed options when editing', () => {
    const existing: RsvpQuestionDraft = {
      id: 'q-existing',
      label: 'help',
      fieldType: 'multiselect',
      options: ['a'],
      required: false,
    };
    const onSave = vi.fn();
    render(<EventRsvpQuestionDialog open existing={existing} onClose={() => {}} onSave={onSave} />);
    fireEvent.change(screen.getByLabelText('options'), { target: { value: 'setup\ncleanup' } });
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));
    expect(onSave).toHaveBeenCalledWith({
      id: 'q-existing',
      label: 'help',
      fieldType: 'multiselect',
      options: ['setup', 'cleanup'],
      required: false,
    });
  });
});
