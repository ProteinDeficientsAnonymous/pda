import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import PlanningScreen from './PlanningScreen';

let years: { id: string; year: number }[] = [];

vi.mock('@/api/planning', () => ({
  usePlanningYears: () => ({ isPending: false, isError: false, data: years }),
}));

beforeEach(() => {
  years = [];
});

describe('PlanningScreen', () => {
  it('shows the empty state when there are no planning years', () => {
    renderWithProviders(<PlanningScreen />);
    expect(screen.getByText('no planning year yet 🌿')).toBeInTheDocument();
  });

  it('defaults the year select to the latest year and lets the planner change it', async () => {
    years = [
      { id: 'y1', year: 2026 },
      { id: 'y2', year: 2028 },
      { id: 'y3', year: 2027 },
    ];
    renderWithProviders(<PlanningScreen />);

    const select = screen.getByLabelText('year');
    expect(select).toHaveValue('2028');
    await userEvent.selectOptions(select, '2026');
    expect(select).toHaveValue('2026');
  });
});
