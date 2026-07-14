import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { RsvpStatus } from '@/models/event';

import { RsvpBox } from './RsvpBox';

const base = {
  open: true,
  initialStatus: RsvpStatus.Attending,
  initialHasPlusOne: false,
  allowPlusOnes: true,
  onClose: () => {},
};

describe('RsvpBox', () => {
  it('shows the note field in create mode', () => {
    render(<RsvpBox {...base} mode="create" onConfirm={() => {}} />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('hides the note field in edit mode', () => {
    render(<RsvpBox {...base} mode="edit" onConfirm={() => {}} />);
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('confirms with status, note, and +1 in create mode', () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="create" onConfirm={onConfirm} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'snacks' } });
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpStatus.Attending, note: 'snacks', hasPlusOne: false }),
    );
  });

  it('omits note in edit mode confirm', () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="edit" onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole('button', { name: /confirm|save/i }));
    expect(onConfirm).toHaveBeenCalledWith(
      expect.not.objectContaining({ note: expect.anything() }),
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
});
