import { fireEvent, render, screen } from '@testing-library/react';
import { addMinutes, format } from 'date-fns';
import { describe, expect, it, vi } from 'vitest';

import { emptyEventFormValues, type EventFormValues } from '@/api/eventWrites';

import { EventFormBasics } from './EventFormBasics';

const START = new Date(2030, 5, 15, 14, 0); // saturday, june 15 2030 · 2:00pm
const END = new Date(2030, 6, 20, 9, 15); // saturday, july 20 2030 · 9:15am

function values(overrides: Partial<EventFormValues> = {}): EventFormValues {
  return { ...emptyEventFormValues(), ...overrides };
}

function renderBasics(overrides: Partial<EventFormValues> = {}, onChange = vi.fn()) {
  return {
    onChange,
    ...render(
      <EventFormBasics
        values={values(overrides)}
        onChange={onChange}
        errors={{}}
        canTagOfficial={false}
        canTagClub={false}
      />,
    ),
  };
}

function dayButton(dayIso: string): HTMLButtonElement {
  const cell = document.querySelector(`[data-day="${dayIso}"]`);
  if (!cell) throw new Error(`no day cell for ${dayIso}`);
  const button = cell.querySelector('button');
  if (!button) throw new Error(`no day button for ${dayIso}`);
  return button as HTMLButtonElement;
}

describe('EventFormBasics poll button gating', () => {
  it('hides the poll button when a fixed date is selected', () => {
    renderBasics({ datetimeTbd: false });
    expect(screen.queryByRole('button', { name: 'poll for dates' })).not.toBeInTheDocument();
    expect(screen.getByText('starts')).toBeInTheDocument();
  });

  it('shows the poll button only once date & time is tbd', () => {
    renderBasics({ datetimeTbd: true });
    expect(screen.getByRole('button', { name: 'poll for dates' })).toBeInTheDocument();
    expect(screen.queryByText('starts')).not.toBeInTheDocument();
  });

  it('hides the poll button when a poll is already active (timeLocked wins over tbd)', () => {
    render(
      <EventFormBasics
        values={values({ datetimeTbd: true })}
        onChange={vi.fn()}
        errors={{}}
        canTagOfficial={false}
        canTagClub={false}
        timeLocked
      />,
    );
    expect(screen.queryByRole('button', { name: 'poll for dates' })).not.toBeInTheDocument();
    expect(screen.getByText(/date locked/)).toBeInTheDocument();
  });
});

describe('EventFormBasics ends picker defaults', () => {
  it('opens on the start day at start+30m and disables earlier days when end is unset', () => {
    const { onChange } = renderBasics({ startDatetime: START.toISOString() });

    fireEvent.click(screen.getByRole('button', { name: 'pick a date & time' }));

    expect(screen.getByText('June 2030')).toBeInTheDocument();
    expect(screen.getByDisplayValue('14:30')).toBeInTheDocument();
    expect(dayButton('2030-06-14')).toBeDisabled();
    expect(dayButton('2030-06-01')).toBeDisabled();
    expect(dayButton('2030-06-15')).toBeEnabled();
    expect(onChange).not.toHaveBeenCalled();
  });

  it('lands a click on the start day at start + 30m', () => {
    const { onChange } = renderBasics({ startDatetime: START.toISOString() });

    fireEvent.click(screen.getByRole('button', { name: 'pick a date & time' }));
    fireEvent.click(dayButton('2030-06-20'));

    expect(onChange).toHaveBeenCalledTimes(1);
    const patch = onChange.mock.calls[0]![0] as Partial<EventFormValues>;
    expect(new Date(patch.endDatetime!)).toEqual(new Date(2030, 5, 20, 14, 30));
  });

  it('a late-night start keeps the end after the start', () => {
    const lateStart = new Date(2030, 5, 15, 23, 45);
    const { onChange } = renderBasics({ startDatetime: lateStart.toISOString() });

    fireEvent.click(screen.getByRole('button', { name: 'pick a date & time' }));

    expect(screen.getByText('June 2030')).toBeInTheDocument();
    expect(screen.getByDisplayValue('00:15')).toBeInTheDocument();

    fireEvent.click(dayButton('2030-06-15'));

    expect(onChange).toHaveBeenCalledTimes(1);
    const patch = onChange.mock.calls[0]![0] as Partial<EventFormValues>;
    expect(new Date(patch.endDatetime!)).toEqual(addMinutes(lateStart, 30));
  });

  it('typing a time before the start snaps to start + 30m', () => {
    const { onChange } = renderBasics({ startDatetime: START.toISOString() });

    fireEvent.click(screen.getByRole('button', { name: 'pick a date & time' }));
    fireEvent.change(screen.getByDisplayValue('14:30'), { target: { value: '09:00' } });

    expect(onChange).toHaveBeenCalledTimes(1);
    const patch = onChange.mock.calls[0]![0] as Partial<EventFormValues>;
    expect(new Date(patch.endDatetime!)).toEqual(addMinutes(START, 30));
  });

  it('clearing the time input does not throw or emit a patch', () => {
    const { onChange } = renderBasics({ startDatetime: START.toISOString() });

    fireEvent.click(screen.getByRole('button', { name: 'pick a date & time' }));
    fireEvent.change(screen.getByDisplayValue('14:30'), { target: { value: '' } });

    expect(onChange).not.toHaveBeenCalled();
  });

  it('keeps the existing end value when one is already set', () => {
    const { onChange } = renderBasics({
      startDatetime: START.toISOString(),
      endDatetime: END.toISOString(),
    });

    fireEvent.click(screen.getByRole('button', { name: 'saturday, july 20 · 9:15am' }));

    expect(screen.getByText('July 2030')).toBeInTheDocument();
    expect(screen.getByDisplayValue('09:15')).toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
  });

  it('leaves the starts picker with its existing defaults', () => {
    const { onChange } = renderBasics();

    fireEvent.click(screen.getAllByRole('button', { name: 'pick a date & time' })[0]!);

    expect(screen.getByText(format(new Date(), 'MMMM yyyy'))).toBeInTheDocument();
    expect(screen.getByDisplayValue('12:00')).toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();

    fireEvent.click(dayButton(format(new Date(), 'yyyy-MM-dd')));
    expect(onChange).toHaveBeenCalledTimes(1);
    const patch = onChange.mock.calls[0]![0] as Partial<EventFormValues>;
    const picked = new Date(patch.startDatetime!);
    expect(picked.getHours()).toBe(12);
    expect(picked.getMinutes()).toBe(0);
  });
});

describe('EventFormBasics start change keeps a valid end', () => {
  const SAME_DAY_END = new Date(2030, 5, 15, 15, 0); // same day as START · 3:00pm

  // Open the starts picker (start is 14:00) and type a new start time.
  function setStartTime(value: string) {
    fireEvent.click(screen.getByRole('button', { name: /· 2:00pm/ }));
    fireEvent.change(screen.getByDisplayValue('14:00'), { target: { value } });
  }

  it('moves an at-or-before end to the new start +30m when the start jumps past it', () => {
    const { onChange } = renderBasics({
      startDatetime: START.toISOString(),
      endDatetime: SAME_DAY_END.toISOString(),
    });

    setStartTime('16:00');

    expect(onChange).toHaveBeenCalledTimes(1);
    const patch = onChange.mock.calls[0]![0] as Partial<EventFormValues>;
    expect(new Date(patch.startDatetime!)).toEqual(new Date(2030, 5, 15, 16, 0));
    expect(new Date(patch.endDatetime!)).toEqual(new Date(2030, 5, 15, 16, 30));
  });

  it('leaves an end still after the new start untouched', () => {
    const { onChange } = renderBasics({
      startDatetime: START.toISOString(),
      endDatetime: SAME_DAY_END.toISOString(),
    });

    setStartTime('14:30');

    expect(onChange).toHaveBeenCalledTimes(1);
    const patch = onChange.mock.calls[0]![0] as Partial<EventFormValues>;
    expect(Object.keys(patch)).toEqual(['startDatetime']);
    expect(new Date(patch.startDatetime!)).toEqual(new Date(2030, 5, 15, 14, 30));
    expect(patch.endDatetime).toBeUndefined();
  });

  it('never fabricates an end when none is set', () => {
    const { onChange } = renderBasics({ startDatetime: START.toISOString() });

    setStartTime('16:00');

    expect(onChange).toHaveBeenCalledTimes(1);
    const patch = onChange.mock.calls[0]![0] as Partial<EventFormValues>;
    expect(Object.keys(patch)).toEqual(['startDatetime']);
    expect(patch.endDatetime).toBeUndefined();
  });
});
