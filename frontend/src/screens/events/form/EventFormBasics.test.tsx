import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { emptyEventFormValues, type EventFormValues } from '@/api/eventWrites';

import { EventFormBasics } from './EventFormBasics';

function values(overrides: Partial<EventFormValues> = {}): EventFormValues {
  return { ...emptyEventFormValues(), ...overrides };
}

function renderBasics(overrides: Partial<EventFormValues> = {}) {
  return render(
    <EventFormBasics
      values={values(overrides)}
      onChange={vi.fn()}
      errors={{}}
      canTagOfficial={false}
      canTagClub={false}
    />,
  );
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
