import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { PlanningGrid } from '@/api/planning';
import { makeSlot } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { ScheduleTab } from './ScheduleTab';

const grid: PlanningGrid = {
  year: 2999,
  slots: [makeSlot({ id: 's1', label: 'january', month: 1, order: 1 })],
  planners: [
    {
      userId: 'u1',
      name: 'ada',
      isPlanner: true,
      hasEmail: true,
      submitted: true,
      biannualInterest: null,
      monthlyCount: 1,
      availableSlotIds: ['s1'],
    },
  ],
  assignments: [],
};

const mutation = { mutateAsync: vi.fn(), isPending: false };

vi.mock('@/api/planning', () => ({
  usePlanningGrid: () => ({ isPending: false, isError: false, data: grid }),
  usePropose: () => mutation,
  useWithdraw: () => mutation,
  useSendProposals: () => mutation,
}));

vi.mock('./PlanningGrid', () => ({
  PlanningGrid: ({ year }: { year: number }) => <div>old table for {year}</div>,
}));

describe('ScheduleTab', () => {
  it('toggles the open month on repeat taps', async () => {
    renderWithProviders(<ScheduleTab year={2999} />);
    const january = screen.getByRole('button', { name: 'open january' });
    await userEvent.click(january);
    expect(january).toHaveAttribute('aria-pressed', 'true');
    await userEvent.click(january);
    expect(january).toHaveAttribute('aria-pressed', 'false');
  });

  it('keeps the old table below the new grid', () => {
    renderWithProviders(<ScheduleTab year={2999} />);
    const january = screen.getByRole('button', { name: 'open january' });
    const old = screen.getByText('old table for 2999');
    expect(january.compareDocumentPosition(old) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
