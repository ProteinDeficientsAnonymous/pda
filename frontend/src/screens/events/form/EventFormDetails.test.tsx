import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { emptyEventFormValues, type EventFormValues } from '@/api/eventWrites';

import { EventFormDetails } from './EventFormDetails';

function values(overrides: Partial<EventFormValues> = {}): EventFormValues {
  return { ...emptyEventFormValues(), ...overrides };
}

describe('EventFormDetails', () => {
  it('shows the visibility dropdown when not locked', () => {
    render(
      <EventFormDetails values={values()} onChange={vi.fn()} errors={{}} typeLocked={false} />,
    );
    expect(screen.getByRole('combobox', { name: 'who can see it' })).toBeInTheDocument();
    expect(screen.queryByText('locked')).not.toBeInTheDocument();
  });

  it('replaces the dropdown with a locked read-out when type-locked', () => {
    render(
      <EventFormDetails
        values={values({ visibility: 'public' })}
        onChange={vi.fn()}
        errors={{}}
        typeLocked
      />,
    );
    expect(screen.queryByRole('combobox', { name: 'who can see it' })).not.toBeInTheDocument();
    expect(screen.getByRole('group', { name: /locked to public/i })).toBeInTheDocument();
    expect(screen.getByText('locked')).toBeInTheDocument();
    expect(screen.getByText('official and club pda events are always public')).toBeInTheDocument();
  });

  it('shows only public in the locked read-out, no struck-through alternatives', () => {
    render(<EventFormDetails values={values()} onChange={vi.fn()} errors={{}} typeLocked />);
    expect(screen.queryByText(/members only/)).not.toBeInTheDocument();
    expect(screen.queryByText(/invite only/)).not.toBeInTheDocument();
  });
});
