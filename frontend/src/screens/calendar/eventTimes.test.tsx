import { render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { makeEvent } from '@/test/fixtures';
import { parseEventDay } from '@/utils/datetime';

import { AgendaList } from './AgendaList';
import { DayEventList } from './DayEventList';
import { NarrowWeekView } from './NarrowWeekView';
import { WideWeekView } from './WideWeekView';

const NOON_ET = new Date('2026-08-12T16:00:00Z');
const FIVE_PM_ET = new Date('2026-08-12T21:00:00Z');
const NEXT_DAY_ET = new Date('2026-08-13T15:00:00Z');
const AUG_12 = parseEventDay('2026-08-12')!;
const LATE_AUG_12_ET = new Date('2026-08-13T03:30:00Z');

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(new Date('2026-08-01T12:00:00Z'));
});

afterEach(() => {
  vi.useRealTimers();
});

describe('DayEventList times', () => {
  function renderDay(endDatetime: Date | null) {
    const event = makeEvent({ title: 'picnic', startDatetime: NOON_ET, endDatetime });
    render(<DayEventList date={AUG_12} events={[event]} onSelectEvent={vi.fn()} />);
  }

  it('labels a start-only event in et', () => {
    renderDay(null);
    expect(screen.getByText('12:00pm et')).toBeInTheDocument();
  });

  it('shows a same-day range in et', () => {
    renderDay(FIVE_PM_ET);
    expect(screen.getByText('12:00pm – 5:00pm et')).toBeInTheDocument();
  });

  it('shows dates for a multi-day range', () => {
    renderDay(NEXT_DAY_ET);
    expect(screen.getByText('aug 12 12:00pm – aug 13 11:00am et')).toBeInTheDocument();
  });
});

describe('AgendaList times', () => {
  it('shows start and end dates for a multi-day event', () => {
    const event = makeEvent({ startDatetime: NOON_ET, endDatetime: NEXT_DAY_ET });
    render(<AgendaList events={[event]} onSelectEvent={vi.fn()} />);
    expect(screen.getByText('wed, aug 12 – thu, aug 13')).toBeInTheDocument();
  });
});

describe('week view chips', () => {
  const event = makeEvent({ title: 'picnic', startDatetime: NOON_ET, endDatetime: FIVE_PM_ET });

  it('narrow view shows the et start time', () => {
    render(
      <NarrowWeekView date={AUG_12} weekStartsOn={0} events={[event]} onSelectEvent={vi.fn()} />,
    );
    expect(screen.getByText(/12:00pm/)).toBeInTheDocument();
  });

  it('wide view shows the et start time', () => {
    render(
      <WideWeekView
        date={AUG_12}
        weekStartsOn={0}
        events={[event]}
        onSelectEvent={vi.fn()}
        onSelectDay={vi.fn()}
      />,
    );
    expect(screen.getByText(/12:00pm/)).toBeInTheDocument();
  });
});

describe('calendar days follow et', () => {
  const late = makeEvent({ title: 'late show', startDatetime: LATE_AUG_12_ET, endDatetime: null });

  it('narrow week puts an 11:30pm et event on its et day', () => {
    render(
      <NarrowWeekView date={AUG_12} weekStartsOn={0} events={[late]} onSelectEvent={vi.fn()} />,
    );
    const wed = screen.getByRole('listitem', { name: 'wed 12' });
    expect(within(wed).getByText('late show')).toBeInTheDocument();
  });

  it('day list includes an 11:30pm et event on its et day', () => {
    render(<DayEventList date={AUG_12} events={[late]} onSelectEvent={vi.fn()} />);
    expect(screen.getByText('11:30pm et')).toBeInTheDocument();
  });
});
