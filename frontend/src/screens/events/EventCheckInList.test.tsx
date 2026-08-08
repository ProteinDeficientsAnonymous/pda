import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { RsvpServerStatus } from '@/models/event';
import { makeGuest } from '@/test/fixtures';

import { EventCheckInList } from './EventCheckInList';

describe('EventCheckInList', () => {
  it('disables no-show but not attended for a cant-go rsvp', () => {
    const guest = makeGuest({ userId: 'u1', name: 'Casey', status: RsvpServerStatus.CantGo });
    render(<EventCheckInList guests={[guest]} onMark={vi.fn()} isPending={false} />);

    expect(screen.getByRole('button', { name: 'attended' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'no-show' })).toBeDisabled();
  });

  it('enables both attendance buttons for a non-cant-go rsvp', () => {
    const guest = makeGuest({ userId: 'u1', name: 'Alice', status: RsvpServerStatus.Attending });
    render(<EventCheckInList guests={[guest]} onMark={vi.fn()} isPending={false} />);

    expect(screen.getByRole('button', { name: 'attended' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'no-show' })).toBeEnabled();
  });
});
