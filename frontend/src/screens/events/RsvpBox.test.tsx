import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { Event } from '@/models/event';
import { RsvpStatus } from '@/models/event';

import { RsvpBox } from './RsvpBox';

const mockUseFlag = vi.hoisted(() => vi.fn(() => true));
vi.mock('@/api/featureFlags', () => ({ useFlag: mockUseFlag }));

function freeEvent(overrides: Partial<Event> = {}): Event {
  return {
    price: '',
    venmoLink: '',
    cashappLink: '',
    zelleInfo: '',
    myPaidConfirmed: false,
    ...overrides,
  } as Event;
}

const base = {
  open: true,
  initialStatus: RsvpStatus.Attending,
  initialHasPlusOne: false,
  allowPlusOnes: true,
  onClose: () => {},
  event: freeEvent(),
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
});

describe('RsvpBox payment confirmation gate', () => {
  const paidEvent = freeEvent({ price: '$10', venmoLink: 'https://venmo.com/u/host' });

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
        event={freeEvent({ ...paidEvent, myPaidConfirmed: true })}
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
