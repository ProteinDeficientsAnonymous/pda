import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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
const propose = vi.fn();
const withdraw = vi.fn();
const toastError = vi.fn();

vi.mock('sonner', () => ({
  toast: {
    error: (m: string) => {
      toastError(m);
    },
  },
}));

vi.mock('@/api/planning', () => ({
  usePlanningGrid: () => ({ isPending: false, isError: false, data: grid }),
  usePropose: () => ({ mutateAsync: propose, isPending: false }),
  useWithdraw: () => ({ mutateAsync: withdraw, isPending: false }),
}));

beforeEach(() => {
  propose.mockReset().mockResolvedValue(undefined);
  withdraw.mockReset().mockResolvedValue(undefined);
  toastError.mockReset();
});

function interactiveGrid(status?: 'proposed' | 'committed' | 'declined'): Grid {
  return {
    year: 2999,
    slots: [slot('s1', 'january', 1)],
    planners: [planner('u1', 'ada', { availableSlotIds: ['s1'] })],
    assignments: status ? [{ id: 'a1', slotId: 's1', userId: 'u1', status }] : [],
  };
}

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

  it.each([undefined, 'declined' as const])(
    'proposes from a cell with status %s',
    async (status) => {
      grid = interactiveGrid(status);
      renderWithProviders(<PlanningGrid year={2999} />);
      await userEvent.click(screen.getByRole('button', { name: 'propose ada for january' }));
      expect(propose).toHaveBeenCalledWith({ slotId: 's1', userId: 'u1' });
    },
  );

  it.each([
    ['proposed', 2999, 'proposed'],
    ['committed', 2999, 'committed'],
    ['proposed', 2000, 'no answer'],
  ] as const)('withdraws a %s cell in %i (%s) after confirming', async (status, year, text) => {
    grid = { ...interactiveGrid(status), year };
    renderWithProviders(<PlanningGrid year={year} />);
    const cell = screen.getByRole('button', { name: 'withdraw ada from january' });
    expect(cell).toHaveAccessibleDescription(text);
    await userEvent.click(cell);
    await userEvent.click(screen.getByRole('button', { name: 'cancel' }));
    expect(withdraw).not.toHaveBeenCalled();
    await userEvent.click(cell);
    await userEvent.click(screen.getByRole('button', { name: 'withdraw' }));
    expect(withdraw).toHaveBeenCalledWith('a1');
  });

  it('toasts when proposing fails', async () => {
    propose.mockRejectedValue(new Error('nope'));
    grid = interactiveGrid();
    renderWithProviders(<PlanningGrid year={2999} />);
    await userEvent.click(screen.getByRole('button', { name: 'propose ada for january' }));
    expect(toastError).toHaveBeenCalledWith("couldn't propose that slot — try again");
  });

  it('disables propose for someone who is no longer a planner but keeps withdraw', () => {
    grid = {
      year: 2999,
      slots: [slot('s1', 'january', 1), slot('s2', 'february', 2)],
      planners: [planner('u1', 'ada', { isPlanner: false })],
      assignments: [{ id: 'a1', slotId: 's2', userId: 'u1', status: 'committed' }],
    };
    renderWithProviders(<PlanningGrid year={2999} />);
    const proposeButton = screen.getByRole('button', { name: 'propose ada for january' });
    expect(proposeButton).toBeDisabled();
    expect(proposeButton).toHaveAccessibleDescription(/no longer a planner/);
    expect(screen.getByRole('button', { name: 'withdraw ada from february' })).toBeEnabled();
  });
});
