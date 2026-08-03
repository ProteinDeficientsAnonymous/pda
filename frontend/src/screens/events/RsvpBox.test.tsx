import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { RsvpStatus } from '@/models/event';

import { RsvpBox } from './RsvpBox';
import type { RsvpQuestionDraft } from './rsvpQuestions';

const base = {
  open: true,
  initialStatus: RsvpStatus.Attending,
  initialHasPlusOne: false,
  allowPlusOnes: true,
  onClose: () => {},
};

const requiredSelect: RsvpQuestionDraft = {
  id: 'q-transport',
  label: 'how are you getting there?',
  fieldType: 'select',
  options: ['driving', 'transit'],
  required: true,
};

const optionalText: RsvpQuestionDraft = {
  id: 'q-notes',
  label: 'anything else?',
  fieldType: 'textarea',
  options: [],
  required: false,
};

describe('RsvpBox', () => {
  it('shows the comment field in create mode', () => {
    render(<RsvpBox {...base} mode="create" onConfirm={() => {}} />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('hides the comment field in edit mode', () => {
    render(<RsvpBox {...base} mode="edit" onConfirm={() => {}} />);
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('confirms with status, comment, and +1 in create mode', () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="create" onConfirm={onConfirm} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'snacks' } });
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({
        status: RsvpStatus.Attending,
        comment: 'snacks',
        hasPlusOne: false,
        answers: {},
      }),
    );
  });

  it('omits comment in edit mode confirm', () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="edit" onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole('button', { name: /confirm|save/i }));
    expect(onConfirm).toHaveBeenCalledWith(
      expect.not.objectContaining({ comment: expect.anything() }),
    );
  });

  it('shows a remove rsvp button in edit mode when onRemove is provided', () => {
    render(<RsvpBox {...base} mode="edit" onConfirm={() => {}} onRemove={() => {}} />);
    expect(screen.getByRole('button', { name: /remove rsvp/i })).toBeInTheDocument();
  });

  it('hides the remove rsvp button in create mode', () => {
    render(<RsvpBox {...base} mode="create" onConfirm={() => {}} onRemove={() => {}} />);
    expect(screen.queryByRole('button', { name: /remove rsvp/i })).not.toBeInTheDocument();
  });

  it('calls onRemove when the remove rsvp button is tapped', () => {
    const onRemove = vi.fn();
    render(<RsvpBox {...base} mode="edit" onConfirm={() => {}} onRemove={onRemove} />);
    fireEvent.click(screen.getByRole('button', { name: /remove rsvp/i }));
    expect(onRemove).toHaveBeenCalled();
  });

  it('disables confirm, cancel, and remove buttons when busy', () => {
    render(<RsvpBox {...base} mode="edit" busy onConfirm={() => {}} onRemove={() => {}} />);
    expect(screen.getByRole('button', { name: /save/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /remove rsvp/i })).toBeDisabled();
  });

  it('toggling only the +1 button in edit mode preserves the initial status', () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="edit" initialHasPlusOne={false} onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole('button', { name: /^add \+1$/i }));
    fireEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpStatus.Attending, hasPlusOne: true }),
    );
  });

  it('keeps the +1 button showing "remove +1" after switching to maybe', () => {
    const onConfirm = vi.fn();
    render(
      <RsvpBox
        {...base}
        mode="edit"
        initialStatus={RsvpStatus.Attending}
        initialHasPlusOne
        onConfirm={onConfirm}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /^maybe$/i }));
    expect(screen.getByRole('button', { name: /^remove \+1$/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpStatus.Maybe, hasPlusOne: true }),
    );
  });

  it('allows removing the +1 after switching to can’t go', () => {
    const onConfirm = vi.fn();
    render(
      <RsvpBox
        {...base}
        mode="edit"
        initialStatus={RsvpStatus.Attending}
        initialHasPlusOne
        onConfirm={onConfirm}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /can't go/i }));
    fireEvent.click(screen.getByRole('button', { name: /^remove \+1$/i }));
    fireEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpStatus.CantGo, hasPlusOne: false }),
    );
  });

  it('hides the +1 button when the event does not allow plus ones', () => {
    render(<RsvpBox {...base} mode="edit" allowPlusOnes={false} onConfirm={() => {}} />);
    expect(screen.queryByRole('button', { name: /\+1/i })).not.toBeInTheDocument();
  });

  it('shows the comment field in edit mode when allowComment is true', () => {
    render(<RsvpBox {...base} mode="edit" allowComment onConfirm={() => {}} />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('hides the comment field in create mode when allowComment is false', () => {
    render(<RsvpBox {...base} mode="create" allowComment={false} onConfirm={() => {}} />);
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('shows "join the waitlist" instead of "i\'m going" when at capacity', () => {
    render(<RsvpBox {...base} mode="create" atCapacity onConfirm={() => {}} />);
    expect(screen.getAllByRole('button', { name: /^join the waitlist$/i })).toHaveLength(2);
    expect(screen.queryByRole('button', { name: /^i'm going$/i })).not.toBeInTheDocument();
  });

  it('confirms with the attending status when joining the waitlist', () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="create" atCapacity onConfirm={onConfirm} />);
    const buttons = screen.getAllByRole('button', { name: /^join the waitlist$/i });
    const confirmButton = buttons.at(-1);
    if (!confirmButton) throw new Error('expected a join the waitlist confirm button');
    fireEvent.click(confirmButton);
    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpStatus.Attending }),
    );
  });

  it('shows questions when attending', () => {
    render(
      <RsvpBox
        {...base}
        mode="create"
        questions={[requiredSelect, optionalText]}
        onConfirm={() => {}}
      />,
    );
    expect(screen.getByText('how are you getting there?')).toBeInTheDocument();
    expect(screen.getByLabelText('anything else? (optional)')).toBeInTheDocument();
  });

  it('hides questions when status is can’t go', () => {
    render(<RsvpBox {...base} mode="create" questions={[requiredSelect]} onConfirm={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /can't go/i }));
    expect(screen.queryByText('how are you getting there?')).not.toBeInTheDocument();
  });

  it('blocks confirm when a required question is unanswered', () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="create" questions={[requiredSelect]} onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent(/required/i);
  });

  it('confirms after answering required questions', () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="create" questions={[requiredSelect]} onConfirm={onConfirm} />);
    fireEvent.change(screen.getByRole('combobox', { name: 'how are you getting there?' }), {
      target: { value: 'driving' },
    });
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({
        status: RsvpStatus.Attending,
        answers: { 'q-transport': 'driving' },
      }),
    );
  });

  it('allows confirm for can’t go without answering required questions', () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="create" questions={[requiredSelect]} onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole('button', { name: /can't go/i }));
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).toHaveBeenCalledWith(expect.objectContaining({ status: RsvpStatus.CantGo }));
  });
});
