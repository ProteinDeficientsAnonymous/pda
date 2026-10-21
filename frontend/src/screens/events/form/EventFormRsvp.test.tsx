import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { emptyEventFormValues, type EventFormValues } from '@/api/eventWrites';
import { EventType } from '@/models/event';

import { EventFormRsvp } from './EventFormRsvp';

function renderRsvp(overrides: Partial<EventFormValues> = {}, onChange = vi.fn()) {
  render(
    <EventFormRsvp
      values={{ ...emptyEventFormValues(), rsvpEnabled: true, ...overrides }}
      onChange={onChange}
      errors={{}}
    />,
  );
  return { onChange, input: screen.getByLabelText('max attendees (optional)') };
}

function Harness({ overrides = {} }: { overrides?: Partial<EventFormValues> }) {
  const [values, setValues] = useState<EventFormValues>({
    ...emptyEventFormValues(),
    rsvpEnabled: true,
    maxAttendees: 15,
    ...overrides,
  });
  return (
    <EventFormRsvp
      values={values}
      onChange={(p) => {
        setValues((v) => ({ ...v, ...p }));
      }}
      errors={{}}
    />
  );
}

describe('max attendees field (issue 1264)', () => {
  it('is not a number input, so scrolling cannot step it', () => {
    const { input } = renderRsvp({ maxAttendees: 15 });
    expect(input).toHaveAttribute('type', 'text');
    expect(input).toHaveAttribute('inputmode', 'numeric');
  });

  it('keeps the value when the page is scrolled over a focused field', () => {
    render(<Harness />);
    const input = screen.getByLabelText('max attendees (optional)') as HTMLInputElement;
    input.focus();

    fireEvent.wheel(input, { deltaY: 100 });

    expect(input.value).toBe('15');
  });

  it('accepts digits', () => {
    const { onChange, input } = renderRsvp({ maxAttendees: null });
    fireEvent.change(input, { target: { value: '12' } });
    expect(onChange).toHaveBeenCalledWith({ maxAttendees: 12 });
  });

  it('strips non-digits rather than storing NaN', () => {
    const { onChange, input } = renderRsvp({ maxAttendees: null });
    fireEvent.change(input, { target: { value: '1e5' } });
    expect(onChange).toHaveBeenCalledWith({ maxAttendees: 15 });
  });

  it('clears to null (unlimited) when emptied', () => {
    const { onChange, input } = renderRsvp({ maxAttendees: 10 });
    fireEvent.change(input, { target: { value: '' } });
    expect(onChange).toHaveBeenCalledWith({ maxAttendees: null });
  });
});

describe('+1s lock for official and club events', () => {
  const plusOnes = () => screen.getByRole('switch', { name: 'allow +1s' });
  const lockNote = '+1s are off for official and club pda events';

  it.each([EventType.Official, EventType.Club])('locks +1s off on %s events', (eventType) => {
    renderRsvp({ eventType, allowPlusOnes: false });
    expect(plusOnes()).toBeDisabled();
    expect(plusOnes()).toHaveAttribute('aria-checked', 'false');
    expect(plusOnes()).toHaveAccessibleDescription(lockNote);
  });

  it('lets an older official event turn +1s off, then locks them off', () => {
    render(<Harness overrides={{ eventType: EventType.Official, allowPlusOnes: true }} />);
    expect(plusOnes()).toBeEnabled();
    expect(screen.queryByText(lockNote)).not.toBeInTheDocument();
    fireEvent.click(plusOnes());
    expect(plusOnes()).toBeDisabled();
    fireEvent.click(plusOnes());
    expect(plusOnes()).toHaveAttribute('aria-checked', 'false');
  });

  it('leaves +1s unlocked on community events', () => {
    renderRsvp({ eventType: EventType.Community, allowPlusOnes: false });
    expect(plusOnes()).toBeEnabled();
    expect(plusOnes()).not.toHaveAccessibleDescription();
    expect(screen.queryByText(lockNote)).not.toBeInTheDocument();
  });
});
