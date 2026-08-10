import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { RsvpStatus } from '@/models/event';
import { makeEvent, makePaidEvent } from '@/test/fixtures';

import { RsvpBox } from './RsvpBox';
import type { RsvpQuestionDraft } from './rsvpQuestions';

const mockUseFlag = vi.hoisted(() => vi.fn(() => true));
vi.mock('@/api/featureFlags', () => ({ useFlag: mockUseFlag }));

const base = {
  open: true,
  initialStatus: RsvpStatus.Attending,
  initialHasPlusOne: false,
  allowPlusOnes: true,
  onClose: () => {},
  event: makeEvent(),
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
        questionnaireResponses: {},
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

  it('should show questions when attending', () => {
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

  it('should keep status controls outside the questions/comment scroll region', () => {
    render(<RsvpBox {...base} mode="create" questions={[requiredSelect]} onConfirm={() => {}} />);
    const scroll = screen.getByTestId('rsvp-details-scroll');
    expect(scroll).toContainElement(screen.getByText('how are you getting there?'));
    expect(scroll).toContainElement(screen.getByLabelText('comment (optional)'));
    expect(scroll).not.toContainElement(screen.getByRole('button', { name: /i'm going/i }));
    expect(scroll).not.toContainElement(screen.getByRole('button', { name: /add \+1/i }));
    expect(scroll).not.toContainElement(screen.getByRole('button', { name: /^confirm$/i }));
  });

  it('should hide questions when status is can’t go', () => {
    render(<RsvpBox {...base} mode="create" questions={[requiredSelect]} onConfirm={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /can't go/i }));
    expect(screen.queryByText('how are you getting there?')).not.toBeInTheDocument();
  });

  it('should block confirm when a required question is unanswered', () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="create" questions={[requiredSelect]} onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByText(/required/i)).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'how are you getting there?' })).toHaveAttribute(
      'aria-invalid',
      'true',
    );
  });

  it('should confirm after answering required questions', () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="create" questions={[requiredSelect]} onConfirm={onConfirm} />);
    fireEvent.change(screen.getByRole('combobox', { name: 'how are you getting there?' }), {
      target: { value: 'driving' },
    });
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({
        status: RsvpStatus.Attending,
        questionnaireResponses: { 'q-transport': 'driving' },
      }),
    );
  });

  it('should allow confirm for can’t go without answering required questions', () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="create" questions={[requiredSelect]} onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole('button', { name: /can't go/i }));
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).toHaveBeenCalledWith(expect.objectContaining({ status: RsvpStatus.CantGo }));
  });
});

describe('RsvpBox payment confirmation gate', () => {
  const paidEvent = makePaidEvent();

  it('shows the payment step before confirming attending on a paid event', async () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} event={paidEvent} mode="create" onConfirm={onConfirm} />);
    await userEvent.click(screen.getByRole('button', { name: /^confirm$/i }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /yes, i paid/i })).toBeInTheDocument();
  });

  it('submits with paidConfirmed after the payment step', async () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} event={paidEvent} mode="create" onConfirm={onConfirm} />);
    await userEvent.click(screen.getByRole('button', { name: /^confirm$/i }));
    await userEvent.click(screen.getByRole('button', { name: /yes, i paid/i }));
    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpStatus.Attending, paidConfirmed: true }),
    );
  });

  it('skips the payment step for maybe', async () => {
    const onConfirm = vi.fn();
    render(
      <RsvpBox
        {...base}
        event={paidEvent}
        mode="create"
        initialStatus={RsvpStatus.Maybe}
        onConfirm={onConfirm}
      />,
    );
    await userEvent.click(screen.getByRole('button', { name: /^confirm$/i }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('skips the payment step on a free event', async () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="create" onConfirm={onConfirm} />);
    await userEvent.click(screen.getByRole('button', { name: /^confirm$/i }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('skips the payment step when the flag is off', async () => {
    mockUseFlag.mockReturnValueOnce(false);
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} event={paidEvent} mode="create" onConfirm={onConfirm} />);
    await userEvent.click(screen.getByRole('button', { name: /^confirm$/i }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('skips the payment step when the viewer already confirmed', async () => {
    const onConfirm = vi.fn();
    render(
      <RsvpBox
        {...base}
        event={makePaidEvent({ myPaidConfirmed: true })}
        mode="edit"
        onConfirm={onConfirm}
      />,
    );
    await userEvent.click(screen.getByRole('button', { name: /^save$/i }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('returns to the picker from the payment step', async () => {
    render(<RsvpBox {...base} event={paidEvent} mode="create" onConfirm={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /^confirm$/i }));
    await userEvent.click(screen.getByRole('button', { name: /back/i }));
    expect(screen.getByRole('button', { name: /^confirm$/i })).toBeInTheDocument();
  });
});
