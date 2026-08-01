import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { EventType } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

import { AgendaList } from './AgendaList';

describe('AgendaList type filter', () => {
  const events = [
    makeEvent({ id: 'a', title: 'official meeting', eventType: EventType.Official }),
    makeEvent({ id: 'b', title: 'community picnic', eventType: EventType.Community }),
  ];

  it('defaults to showing all event types', () => {
    render(<AgendaList events={events} onSelectEvent={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'official meeting' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'community picnic' })).toBeInTheDocument();
  });

  it('filters to pda official only', async () => {
    const user = userEvent.setup();
    render(<AgendaList events={events} onSelectEvent={vi.fn()} />);
    await user.click(screen.getByRole('radio', { name: 'pda official' }));
    expect(screen.getByRole('button', { name: 'official meeting' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'community picnic' })).not.toBeInTheDocument();
  });

  it('filters to community only', async () => {
    const user = userEvent.setup();
    render(<AgendaList events={events} onSelectEvent={vi.fn()} />);
    await user.click(screen.getByRole('radio', { name: 'community' }));
    expect(screen.queryByRole('button', { name: 'official meeting' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'community picnic' })).toBeInTheDocument();
  });

  it('shows a filter-aware empty state when no events match', async () => {
    const user = userEvent.setup();
    const communityOnly = [makeEvent({ eventType: EventType.Community })];
    render(<AgendaList events={communityOnly} onSelectEvent={vi.fn()} />);
    await user.click(screen.getByRole('radio', { name: 'pda official' }));
    expect(screen.getByText('no pda official events coming up')).toBeInTheDocument();
  });
});

describe('AgendaList upcoming filter', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-08-01T14:00:00'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('excludes events that already ended earlier today', () => {
    const events = [
      makeEvent({
        id: 'ended',
        title: 'morning standup',
        startDatetime: new Date('2026-08-01T10:00:00'),
        endDatetime: new Date('2026-08-01T11:00:00'),
      }),
      makeEvent({
        id: 'later',
        title: 'evening social',
        startDatetime: new Date('2026-08-01T18:00:00'),
        endDatetime: new Date('2026-08-01T20:00:00'),
      }),
    ];
    render(<AgendaList events={events} onSelectEvent={vi.fn()} />);
    expect(screen.queryByRole('button', { name: 'morning standup' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'evening social' })).toBeInTheDocument();
  });
});
