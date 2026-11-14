import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
import { Permission } from '@/models/permissions';
import { makeUser } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import PlanningScreen from './PlanningScreen';

let years: { id: string; year: number }[] = [];

const createYear = vi.fn();
const toastError = vi.fn();

vi.mock('sonner', () => ({
  toast: {
    error: (m: string) => {
      toastError(m);
    },
  },
}));

vi.mock('@/api/planning', () => ({
  usePlanningYears: () => ({ isPending: false, isError: false, data: years }),
  useCreateYear: () => ({ mutateAsync: createYear, isPending: false }),
}));

function signInWith(...perms: string[]) {
  const roles = [{ id: 'r1', name: 'planner', isDefault: false, permissions: perms }];
  useAuthStore.setState({ status: 'authed', user: makeUser({ roles }), accessToken: 'tok' });
}

vi.mock('./MySlots', () => ({
  MySlots: () => <div>my slots</div>,
}));

vi.mock('./AvailabilityForm', () => ({
  AvailabilityForm: ({ year }: { year: number }) => <div>form for {year}</div>,
}));

vi.mock('./PlanningGrid', () => ({
  PlanningGrid: ({ year }: { year: number }) => <div>grid for {year}</div>,
}));

vi.mock('./SlotEditor', () => ({
  SlotEditor: ({ year }: { year: number }) => <div>editor for {year}</div>,
}));

beforeEach(() => {
  years = [];
  toastError.mockReset();
  createYear.mockReset().mockResolvedValue({ id: 'new', year: 0 });
  signInWith(Permission.ViewEventPlanning);
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
    expect(screen.getByText('form for 2028')).toBeInTheDocument();
    await userEvent.selectOptions(select, '2026');
    expect(select).toHaveValue('2026');
    expect(screen.getByText('form for 2026')).toBeInTheDocument();
  });

  it('shows my slots above the availability form', () => {
    years = [{ id: 'y1', year: 2026 }];
    renderWithProviders(<PlanningScreen />);
    const mine = screen.getByText('my slots');
    const form = screen.getByText('form for 2026');
    expect(mine.compareDocumentPosition(form) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('shows the slot editor and grid to managers only', () => {
    years = [{ id: 'y1', year: 2026 }];
    const { unmount } = renderWithProviders(<PlanningScreen />);
    expect(screen.queryByText('editor for 2026')).not.toBeInTheDocument();
    expect(screen.queryByText('grid for 2026')).not.toBeInTheDocument();
    unmount();

    signInWith(Permission.ManageEventPlanning);
    renderWithProviders(<PlanningScreen />);
    expect(screen.getByText('editor for 2026')).toBeInTheDocument();
    expect(screen.getByText('grid for 2026')).toBeInTheDocument();
  });

  describe('start next year', () => {
    const nextYear = new Date().getFullYear() + 1;

    it('lets a manager start next year and selects it', async () => {
      signInWith(Permission.ManageEventPlanning);
      years = [{ id: 'y1', year: nextYear - 1 }];
      renderWithProviders(<PlanningScreen />);

      await userEvent.click(screen.getByRole('button', { name: `start ${String(nextYear)}` }));
      expect(createYear).toHaveBeenCalledWith(nextYear);
      expect(await screen.findByText(`form for ${String(nextYear)}`)).toBeInTheDocument();
    });

    it('lets a manager start next year from the empty state', () => {
      signInWith(Permission.ManageEventPlanning);
      renderWithProviders(<PlanningScreen />);
      expect(screen.getByRole('button', { name: `start ${String(nextYear)}` })).toBeInTheDocument();
    });

    it('stays put and toasts when starting the year fails', async () => {
      signInWith(Permission.ManageEventPlanning);
      years = [{ id: 'y1', year: nextYear - 1 }];
      createYear.mockRejectedValue(new Error('boom'));
      renderWithProviders(<PlanningScreen />);

      await userEvent.click(screen.getByRole('button', { name: `start ${String(nextYear)}` }));
      expect(toastError).toHaveBeenCalledWith("couldn't start that year — try again");
      expect(screen.queryByText(`form for ${String(nextYear)}`)).not.toBeInTheDocument();
    });

    it('hides the button from planners who cannot manage', () => {
      years = [{ id: 'y1', year: nextYear - 1 }];
      renderWithProviders(<PlanningScreen />);
      expect(screen.queryByRole('button', { name: /^start / })).not.toBeInTheDocument();
    });

    it('hides the button once next year exists', () => {
      signInWith(Permission.ManageEventPlanning);
      years = [{ id: 'y1', year: nextYear }];
      renderWithProviders(<PlanningScreen />);
      expect(screen.queryByRole('button', { name: /^start / })).not.toBeInTheDocument();
    });
  });
});
