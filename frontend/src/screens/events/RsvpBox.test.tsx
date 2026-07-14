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
});
