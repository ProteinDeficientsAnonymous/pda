import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Permission } from '@/models/permissions';
import { setAuthed } from '@/test/auth';
import { makeUserWithPermissions } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import PlanningScreen from './PlanningScreen';

let years: { id: string; year: number }[] = [];
let mySlots: { isPending?: boolean; data?: { status: string }[] } = { data: [] };

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
  useMySlots: () => mySlots,
  useCreateYear: () => ({ mutateAsync: createYear, isPending: false }),
}));

function signInWith(...perms: string[]) {
  setAuthed(makeUserWithPermissions(perms));
}

vi.mock('./MySlots', () => ({
  MySlots: () => <div>my slots</div>,
}));

vi.mock('./AvailabilityForm', () => ({
  AvailabilityForm: ({ year }: { year: number }) => <div>form for {year}</div>,
}));

vi.mock('./ScheduleTab', () => ({
  ScheduleTab: ({ year }: { year: number }) => <div>grid for {year}</div>,
}));

vi.mock('./ChecklistTab', () => ({
  ChecklistTab: () => <div>checklist tab</div>,
}));

vi.mock('./GuidelinesTab', () => ({
  GuidelinesTab: () => <div>guidelines tab</div>,
}));

vi.mock('./SlotEditor', () => ({
  SlotEditor: ({ year }: { year: number }) => <div>editor for {year}</div>,
}));

beforeEach(() => {
  years = [];
  mySlots = { data: [] };
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
    renderWithProviders(<PlanningScreen />, { route: '/?tab=availability' });

    const select = screen.getByLabelText('year');
    expect(select).toHaveValue('2028');
    expect(screen.getByText('form for 2028')).toBeInTheDocument();
    await userEvent.selectOptions(select, '2026');
    expect(select).toHaveValue('2026');
    expect(screen.getByText('form for 2026')).toBeInTheDocument();
  });

  it('splits my events and my availability into their own tabs', async () => {
    years = [{ id: 'y1', year: 2026 }];
    renderWithProviders(<PlanningScreen />);
    expect(screen.queryByText('form for 2026')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('radio', { name: 'my availability' }));
    expect(screen.getByText('form for 2026')).toBeInTheDocument();
    expect(screen.queryByText('my slots')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('radio', { name: 'checklist' }));
    expect(screen.getByText('checklist tab')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('radio', { name: 'guidelines' }));
    expect(screen.getByText('guidelines tab')).toBeInTheDocument();
  });

  describe('tabs', () => {
    const manage = () => {
      signInWith(Permission.ManageEventPlanning);
      years = [{ id: 'y1', year: 2027 }];
    };

    it('opens a coordinator on the schedule tab', () => {
      manage();
      renderWithProviders(<PlanningScreen />);
      expect(screen.getByRole('radiogroup', { name: 'planning view' })).toBeInTheDocument();
      expect(screen.getByRole('radio', { name: 'schedule' })).toBeChecked();
      expect(screen.getByText('grid for 2027')).toBeInTheDocument();
      expect(screen.queryByText('form for 2027')).not.toBeInTheDocument();
    });

    it('opens my events from the old ?tab=mine link', () => {
      manage();
      renderWithProviders(<PlanningScreen />, { route: '/?tab=mine' });
      expect(screen.getByRole('radio', { name: 'my events' })).toBeChecked();
      expect(screen.getByText('my slots')).toBeInTheDocument();
      expect(screen.queryByText('grid for 2027')).not.toBeInTheDocument();
    });

    it('defaults to my events when a slot is waiting on the user', () => {
      manage();
      mySlots = { data: [{ status: 'proposed' }] };
      renderWithProviders(<PlanningScreen />);
      expect(screen.getByRole('radio', { name: 'my events' })).toBeChecked();
      expect(screen.getByText('my slots')).toBeInTheDocument();
    });

    it('shows the slot editor and start button on the slots tab only', async () => {
      const current = new Date().getFullYear();
      signInWith(Permission.ManageEventPlanning);
      years = [{ id: 'y1', year: current }];
      renderWithProviders(<PlanningScreen />);
      expect(screen.queryByRole('button', { name: /^start / })).not.toBeInTheDocument();
      await userEvent.click(screen.getByRole('radio', { name: 'slots' }));
      const editor = screen.getByText(`editor for ${String(current)}`);
      const start = screen.getByRole('button', { name: `start ${String(current + 1)}` });
      expect(editor.compareDocumentPosition(start) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it('keeps my events selected after the waiting slot is answered', () => {
      manage();
      mySlots = { data: [{ status: 'proposed' }] };
      const { rerender } = renderWithProviders(<PlanningScreen />);
      mySlots = { data: [{ status: 'committed' }] };
      rerender(<PlanningScreen />);
      expect(screen.getByRole('radio', { name: 'my events' })).toBeChecked();
      expect(screen.queryByText('grid for 2027')).not.toBeInTheDocument();
    });

    it('waits for my slots before picking a default tab', () => {
      manage();
      mySlots = { isPending: true };
      renderWithProviders(<PlanningScreen />);
      expect(screen.queryByText('grid for 2027')).not.toBeInTheDocument();
      expect(screen.queryByText('my slots')).not.toBeInTheDocument();
      expect(screen.queryByText('editor for 2027')).not.toBeInTheDocument();
    });

    it('settles a bogus ?tab= on the default and keeps it after the slot is answered', () => {
      manage();
      mySlots = { isPending: true };
      const { rerender } = renderWithProviders(<PlanningScreen />, { route: '/?tab=bogus' });
      expect(screen.queryByText('grid for 2027')).not.toBeInTheDocument();
      expect(screen.getByRole('radio', { name: 'schedule' })).not.toBeChecked();
      mySlots = { data: [{ status: 'proposed' }] };
      rerender(<PlanningScreen />);
      expect(screen.getByRole('radio', { name: 'my events' })).toBeChecked();
      mySlots = { data: [{ status: 'committed' }] };
      rerender(<PlanningScreen />);
      expect(screen.getByRole('radio', { name: 'my events' })).toBeChecked();
      expect(screen.queryByText('grid for 2027')).not.toBeInTheDocument();
    });

    it('does not wait for my slots when the tab is explicit', () => {
      manage();
      mySlots = { isPending: true };
      renderWithProviders(<PlanningScreen />, { route: '/?tab=schedule' });
      expect(screen.getByText('grid for 2027')).toBeInTheDocument();
    });

    it.each(['/', '/?tab=slots'])(
      'opens planners who cannot manage on my events at %s',
      (route) => {
        years = [{ id: 'y1', year: 2027 }];
        renderWithProviders(<PlanningScreen />, { route });
        expect(screen.getAllByRole('radio')).toHaveLength(5);
        expect(screen.getByRole('radio', { name: 'schedule' })).toBeInTheDocument();
        expect(screen.getByRole('radio', { name: 'my events' })).toBeChecked();
        expect(screen.getByRole('radio', { name: 'my availability' })).toBeInTheDocument();
        expect(screen.getByText('my slots')).toBeInTheDocument();
        expect(screen.queryByText('grid for 2027')).not.toBeInTheDocument();
        expect(screen.queryByText('editor for 2027')).not.toBeInTheDocument();
      },
    );

    it('lets planners who cannot manage open the schedule', () => {
      years = [{ id: 'y1', year: 2027 }];
      renderWithProviders(<PlanningScreen />, { route: '/?tab=schedule' });
      expect(screen.getByText('grid for 2027')).toBeInTheDocument();
    });
  });

  describe('start next year', () => {
    const nextYear = new Date().getFullYear() + 1;

    it('lets a manager start next year and selects it', async () => {
      signInWith(Permission.ManageEventPlanning);
      years = [{ id: 'y1', year: nextYear - 1 }];
      renderWithProviders(<PlanningScreen />, { route: '/?tab=slots' });

      await userEvent.click(screen.getByRole('button', { name: `start ${String(nextYear)}` }));
      expect(createYear).toHaveBeenCalledWith(nextYear);
      expect(await screen.findByText(`editor for ${String(nextYear)}`)).toBeInTheDocument();
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
      renderWithProviders(<PlanningScreen />, { route: '/?tab=slots' });

      await userEvent.click(screen.getByRole('button', { name: `start ${String(nextYear)}` }));
      expect(toastError).toHaveBeenCalledWith("couldn't start that year — try again");
      expect(screen.queryByText(`editor for ${String(nextYear)}`)).not.toBeInTheDocument();
    });

    it('hides the button from planners who cannot manage', () => {
      years = [{ id: 'y1', year: nextYear - 1 }];
      renderWithProviders(<PlanningScreen />, { route: '/?tab=slots' });
      expect(screen.queryByRole('button', { name: /^start / })).not.toBeInTheDocument();
    });

    it('offers the year after the latest one', () => {
      signInWith(Permission.ManageEventPlanning);
      years = [
        { id: 'y1', year: nextYear },
        { id: 'y2', year: nextYear - 1 },
      ];
      renderWithProviders(<PlanningScreen />, { route: '/?tab=slots' });
      expect(
        screen.getByRole('button', { name: `start ${String(nextYear + 1)}` }),
      ).toBeInTheDocument();
    });
  });
});
