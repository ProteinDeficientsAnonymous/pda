import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { Event } from '@/models/event';
import { RsvpServerStatus } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }));

import { GroupTextButton } from './GroupTextButton';

function guest(overrides: Partial<Event['guests'][number]>): Event['guests'][number] {
  return {
    userId: 'u',
    name: 'someone',
    status: RsvpServerStatus.Attending,
    phone: null,
    photoUrl: '',
    hasPlusOne: false,
    attendance: 'unknown',
    ...overrides,
  };
}

const EVENT = makeEvent({
  guests: [guest({ userId: 'a', phone: '+15551112222', status: RsvpServerStatus.Attending })],
});

describe('GroupTextButton', () => {
  it('renders a trigger and opens the picker dialog on click', () => {
    render(<GroupTextButton event={EVENT} />);
    // Dialog is closed initially.
    expect(screen.queryByRole('dialog')).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: 'group text' }));
    expect(screen.getByRole('dialog', { name: 'group text' })).toBeInTheDocument();
  });

  it('renders nothing when no group has a reachable number', () => {
    const event = makeEvent({
      guests: [guest({ userId: 'a', phone: null, status: RsvpServerStatus.Attending })],
      invitedUserPhones: [],
    });
    const { container } = render(<GroupTextButton event={event} />);
    expect(container).toBeEmptyDOMElement();
  });
});
