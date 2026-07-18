import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

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
