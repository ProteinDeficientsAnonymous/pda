import { screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { PlanningGrid as Grid } from '@/api/planning';
import { renderWithProviders } from '@/test/render';

import { PlanningGrid } from './PlanningGrid';

const slot = (id: string, label: string, month: number, event?: string) => ({
  id,
  label,
  month,
  kind: 'monthly' as const,
  order: month,
  eventId: event ?? null,
  eventSlug: event ? 'jan-potluck' : null,
  eventStatus: null,
});

const planner = (userId: string, name: string, extra: object = {}) => ({
  userId,
  name,
  isPlanner: true,
  hasEmail: true,
  submitted: true,
  biannualInterest: 'yes' as const,
  monthlyCount: 2,
  availableSlotIds: [] as string[],
  ...extra,
});

let grid: Grid;

vi.mock('@/api/planning', () => ({
  usePlanningGrid: () => ({ isPending: false, isError: false, data: grid }),
}));

describe('PlanningGrid', () => {
  it('shows planner info, cell state text and scheduled slots', () => {
    grid = {
      year: 2999,
      slots: [slot('s1', 'january', 1, 'e1'), slot('s2', 'february', 2)],
      planners: [
        planner('u1', 'ada', { availableSlotIds: ['s2'] }),
        planner('u2', 'bo', { submitted: false, hasEmail: false }),
      ],
      assignments: [{ id: 'a1', slotId: 's1', userId: 'u1', status: 'committed' }],
    };
    renderWithProviders(<PlanningGrid year={2999} />);

    expect(screen.getByText('biannual: yes · monthly: 2')).toBeInTheDocument();
    expect(screen.getByText('not submitted')).toBeInTheDocument();
    expect(screen.getByText('no email')).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'planning grid' })).toBeInTheDocument();
    const january = screen.getByRole('row', { name: /january/ });
    expect(within(january).getByText('committed')).toBeInTheDocument();
    expect(within(january).getByText('not available')).toBeInTheDocument();
    expect(within(january).getByRole('link', { name: 'view event' })).toHaveAttribute(
      'href',
      '/events/jan-potluck',
    );
    expect(within(january).getByText(/scheduled/)).toBeInTheDocument();
    expect(
      within(screen.getByRole('row', { name: /february/ })).getByText('available'),
    ).toBeVisible();
  });

  it('shows the empty state without planners', () => {
    grid = { year: 2999, slots: [], planners: [], assignments: [] };
    renderWithProviders(<PlanningGrid year={2999} />);
    expect(screen.getByText('no planners yet 🌿')).toBeInTheDocument();
  });
});
