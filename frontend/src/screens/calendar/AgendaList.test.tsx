import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { EventType } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

import { AgendaList } from './AgendaList';

describe('AgendaList', () => {
  it('renders all upcoming events', () => {
    const events = [
      makeEvent({ id: 'a', title: 'official meeting', eventType: EventType.Official }),
      makeEvent({ id: 'b', title: 'community picnic', eventType: EventType.Community }),
    ];
    render(<AgendaList events={events} onSelectEvent={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'official meeting' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'community picnic' })).toBeInTheDocument();
  });

  it('shows an empty state when there are no upcoming events', () => {
    render(<AgendaList events={[]} onSelectEvent={vi.fn()} />);
    expect(screen.getByText('nothing on the horizon — pop back later')).toBeInTheDocument();
  });
});
