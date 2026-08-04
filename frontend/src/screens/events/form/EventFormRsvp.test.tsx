import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { emptyEventFormValues, type EventFormValues } from '@/api/eventWrites';

import { EventFormRsvp } from './EventFormRsvp';

function renderRsvp(overrides: Partial<EventFormValues> = {}) {
  return render(
    <EventFormRsvp
      values={{ ...emptyEventFormValues(), rsvpEnabled: true, ...overrides }}
      onChange={vi.fn()}
      errors={{}}
    />,
  );
}

describe('max attendees field (issue 1264)', () => {
  // Hiding the spinners doesn't disable stepping — the field still steps on
  // wheel/arrow keys, so the value changed with no visible control to explain
  // it. Keep the arrows visible rather than hiding a live affordance.
  it('does not hide the number input spinners', () => {
    renderRsvp({ maxAttendees: 15 });
    const input = screen.getByLabelText('max attendees (optional)');
    expect(input.className).not.toMatch(/spin-button/);
    expect(input.className).not.toMatch(/moz-appearance/);
  });
});
