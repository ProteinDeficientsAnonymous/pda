import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { PlanningGrid as Grid } from '@/api/planning';
import { makeSlot } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { PlanningGrid } from './PlanningGrid';

const slot = (id: string, label: string, month: number, event?: string) =>
  makeSlot({
    id,
    label,
    month,
    order: month,
    ...(event ? { eventId: event, eventSlug: 'jan-potluck', eventStatus: 'active' } : {}),
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
const sendProposals = vi.fn();
const toastError = vi.fn();
const toastSuccess = vi.fn();

vi.mock('sonner', () => ({
  toast: {
    error: (m: string) => {
      toastError(m);
    },
    success: (m: string) => {
      toastSuccess(m);
    },
  },
}));

vi.mock('@/api/planning', () => ({
  usePlanningGrid: () => ({ isPending: false, isError: false, data: grid }),
  usePropose: () => ({ mutateAsync: propose, isPending: false }),
  useWithdraw: () => ({ mutateAsync: withdraw, isPending: false }),
  useSendProposals: () => ({ mutateAsync: sendProposals, isPending: false }),
}));

beforeEach(() => {
  propose.mockReset().mockResolvedValue(undefined);
  withdraw.mockReset().mockResolvedValue(undefined);
  sendProposals.mockReset().mockResolvedValue({ planners_notified: 3, proposals_sent: 5 });
  toastError.mockReset();
  toastSuccess.mockReset();
});

function interactiveGrid(status?: 'draft' | 'proposed' | 'committed' | 'declined'): Grid {
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
    expect(within(january).getByText(/scheduled ·/)).toBeInTheDocument();
    expect(
      within(screen.getByRole('row', { name: /february/ })).getByText('available'),
    ).toBeVisible();
  });

  it('offers create event only on slots with a committed planner', () => {
    grid = {
      year: 2999,
      slots: [slot('s1', 'january', 1), slot('s2', 'february', 2)],
      planners: [planner('u1', 'ada'), planner('u2', 'bo')],
      assignments: [
        { id: 'a1', slotId: 's1', userId: 'u1', status: 'committed' },
        { id: 'a2', slotId: 's2', userId: 'u2', status: 'proposed' },
      ],
    };
    renderWithProviders(<PlanningGrid year={2999} />);
    const january = screen.getByRole('row', { name: /january/ });
    expect(within(january).getByRole('link', { name: 'create event' })).toBeInTheDocument();
    const february = screen.getByRole('row', { name: /february/ });
    expect(within(february).queryByRole('link')).not.toBeInTheDocument();
  });

  it.each([
    ['only declines', ['declined'], true],
    ['a decline and a proposal', ['declined', 'proposed'], false],
    ['a decline and a commit', ['declined', 'committed'], false],
    ['a decline and a draft', ['declined', 'draft'], false],
    ['no assignments', [], false],
  ] as const)('flags needs a planner with %s: %s', (_name, statuses, flagged) => {
    grid = {
      year: 2999,
      slots: [slot('s1', 'january', 1)],
      planners: [planner('u1', 'ada'), planner('u2', 'bo')],
      assignments: statuses.map((status, i) => ({
        id: `a${String(i)}`,
        slotId: 's1',
        userId: `u${String(i + 1)}`,
        status,
      })),
    };
    renderWithProviders(<PlanningGrid year={2999} />);
    const january = screen.getByRole('row', { name: /january/ });
    expect(within(january).queryByText('needs a planner') !== null).toBe(flagged);
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

  it('removes a draft straight away without confirming', async () => {
    grid = interactiveGrid('draft');
    renderWithProviders(<PlanningGrid year={2999} />);
    const cell = screen.getByRole('button', { name: 'remove draft ada for january' });
    expect(cell).toHaveAccessibleDescription('draft');
    await userEvent.click(cell);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(withdraw).toHaveBeenCalledWith('a1');
  });

  it('hides send proposals without drafts', () => {
    grid = interactiveGrid('proposed');
    renderWithProviders(<PlanningGrid year={2999} />);
    expect(screen.queryByRole('button', { name: /^send/ })).not.toBeInTheDocument();
  });

  it.each([
    [1, 'send 1 proposal'],
    [2, 'send 2 proposals'],
  ])('labels send for %i drafts', (count, label) => {
    grid = {
      ...interactiveGrid(),
      assignments: Array.from({ length: count }, (_, i) => ({
        id: `a${String(i)}`,
        slotId: 's1',
        userId: `u${String(i)}`,
        status: 'draft' as const,
      })),
    };
    renderWithProviders(<PlanningGrid year={2999} />);
    expect(screen.getByRole('button', { name: label })).toBeInTheDocument();
    expect(screen.getByText("drafts aren't sent until you hit send")).toBeInTheDocument();
  });

  it('sends the drafts and toasts who was notified', async () => {
    grid = interactiveGrid('draft');
    renderWithProviders(<PlanningGrid year={2999} />);
    await userEvent.click(screen.getByRole('button', { name: 'send 1 proposal' }));
    expect(sendProposals).toHaveBeenCalled();
    expect(toastSuccess).toHaveBeenCalledWith('sent to 3 planners 🌱');
  });

  it('toasts when sending fails', async () => {
    sendProposals.mockRejectedValue(new Error('nope'));
    grid = interactiveGrid('draft');
    renderWithProviders(<PlanningGrid year={2999} />);
    await userEvent.click(screen.getByRole('button', { name: 'send 1 proposal' }));
    expect(toastError).toHaveBeenCalledWith("couldn't send proposals — try again");
    expect(toastSuccess).not.toHaveBeenCalled();
  });
});
