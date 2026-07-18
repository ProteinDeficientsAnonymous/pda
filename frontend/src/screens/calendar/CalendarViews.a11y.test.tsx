import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

import { makeEvent } from '@/test/fixtures';

import { AgendaList } from './AgendaList';
import { DayEventList } from './DayEventList';

describe('calendar views accessibility', () => {
  it('AgendaList exposes each event as a button labelled with its title', () => {
    const events = [
      makeEvent({ id: 'a', title: 'movie night' }),
      makeEvent({ id: 'b', title: 'beach cleanup' }),
    ];
    render(<AgendaList events={events} onSelectEvent={vi.fn()} />);

    expect(screen.getByRole('button', { name: 'movie night' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'beach cleanup' })).toBeInTheDocument();
  });

  it('AgendaList has no axe violations with events', async () => {
    const events = [makeEvent()];
    const { container } = render(<AgendaList events={events} onSelectEvent={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('AgendaList empty state has no axe violations', async () => {
    const { container } = render(<AgendaList events={[]} onSelectEvent={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('DayEventList exposes each event as a button labelled with its title', () => {
    const target = new Date();
    target.setHours(18, 0, 0, 0);
    const events = [makeEvent({ id: 'a', title: 'dinner', startDatetime: target })];

    render(<DayEventList date={target} events={events} onSelectEvent={vi.fn()} />);

    expect(screen.getByRole('button', { name: 'dinner' })).toBeInTheDocument();
  });
});
